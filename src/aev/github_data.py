"""Fetch issue and pull request history from GitHub.

Uses the GitHub GraphQL API with the workflow's built-in GITHUB_TOKEN; no
personal access token is needed. The result is a "snapshot" (plain data, see
items.py) so the calculation never depends on GitHub directly.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

API_URL = "https://api.github.com/graphql"

# GitHub's "Revert" button writes "Reverts owner/repo#123" in the PR body.
REVERT_BODY = re.compile(r"Reverts\s+[\w.-]+/[\w.-]+#(\d+)", re.IGNORECASE)

ISSUES_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        labels(first: 50) { nodes { name } }
        closedByPullRequestsReferences(first: 25, includeClosedPrs: true) {
          nodes { number mergedAt author { login } }
        }
        timelineItems(first: 100, itemTypes: [CLOSED_EVENT, REOPENED_EVENT]) {
          nodes {
            __typename
            ... on ClosedEvent {
              createdAt
              stateReason
              closer { __typename ... on PullRequest { number mergedAt author { login } } }
            }
            ... on ReopenedEvent { createdAt }
          }
        }
      }
    }
  }
}
"""

MERGED_PRS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: 100, after: $cursor,
                 orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { number title body mergedAt updatedAt }
    }
  }
}
"""


# Labels and commit authors (including Co-authored-by trailers) of merged PRs,
# used to decide whether a PR is agent, human or mixed work. Fetched in
# batches, one aliased pullRequest field per PR.
PR_DETAILS_FIELDS = """
      number
      labels(first: 50) { nodes { name } }
      commits(first: 100) {
        totalCount
        nodes { commit { authors(first: 10) { nodes { name email user { login } } } } }
      }
"""

PR_DETAILS_BATCH = 20


def pr_details_query(numbers: List[int]) -> str:
    fields = "\n".join(
        f"    pr{n}: pullRequest(number: {int(n)}) {{{PR_DETAILS_FIELDS}    }}" for n in numbers
    )
    return (
        "query($owner: String!, $name: String!) {\n"
        "  repository(owner: $owner, name: $name) {\n"
        f"{fields}\n"
        "  }\n"
        "}\n"
    )


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str, api_url: str = API_URL):
        if not token:
            raise GitHubError(
                "No GitHub token found. In a workflow this is provided "
                "automatically as GITHUB_TOKEN."
            )
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "User-Agent": "aev-reference-tool"}
        )

    def query(self, query: str, variables: dict) -> dict:
        last_error: Optional[str] = None
        for attempt in range(4):
            try:
                response = self.session.post(
                    self.api_url, json={"query": query, "variables": variables}, timeout=60
                )
            except requests.RequestException as exc:
                last_error = str(exc)
            else:
                if response.status_code == 200:
                    payload = response.json()
                    if payload.get("errors"):
                        raise GitHubError(f"GitHub API error: {payload['errors']}")
                    return payload["data"]
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                if response.status_code not in (403, 502, 503, 504):
                    break
            time.sleep(2 ** attempt)
        raise GitHubError(f"GitHub request failed: {last_error}")


def _login(node: Optional[dict]) -> Optional[str]:
    author = (node or {}).get("author") or {}
    return author.get("login")


def fetch_reverts(client: GitHubClient, owner: str, name: str, since: datetime) -> Dict[int, str]:
    """Map 'PR number that was reverted' -> 'time the revert PR was merged'."""
    reverts: Dict[int, str] = {}
    cursor = None
    while True:
        data = client.query(MERGED_PRS_QUERY, {"owner": owner, "name": name, "cursor": cursor})
        page = data["repository"]["pullRequests"]
        stop = False
        for pr in page["nodes"]:
            updated = datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
            if updated < since:
                stop = True  # sorted newest first; nothing older can matter
                break
            match = REVERT_BODY.search(pr.get("body") or "")
            if match and pr.get("mergedAt"):
                original = int(match.group(1))
                previous = reverts.get(original)
                if previous is None or pr["mergedAt"] < previous:
                    reverts[original] = pr["mergedAt"]
        if stop or not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return reverts


def pr_details_from_node(node: dict) -> dict:
    """Turn one pullRequest node into {"labels", "commits", "commits_truncated"}."""
    commits = []
    for commit_node in node["commits"]["nodes"]:
        authors = []
        for author in commit_node["commit"]["authors"]["nodes"]:
            user = author.get("user") or {}
            authors.append({
                "login": user.get("login"),
                "name": author.get("name"),
                "email": author.get("email"),
            })
        commits.append({"authors": authors})
    return {
        "labels": [label["name"] for label in node["labels"]["nodes"]],
        "commits": commits,
        "commits_truncated": node["commits"]["totalCount"] > len(commits),
    }


def fetch_pr_details(client: GitHubClient, owner: str, name: str, numbers: List[int]) -> Dict[int, dict]:
    """Labels and commit authors for each PR number, fetched in batches."""
    details: Dict[int, dict] = {}
    numbers = sorted(set(numbers))
    for start in range(0, len(numbers), PR_DETAILS_BATCH):
        batch = numbers[start:start + PR_DETAILS_BATCH]
        data = client.query(pr_details_query(batch), {"owner": owner, "name": name})
        for n in batch:
            node = data["repository"].get(f"pr{n}")
            if node:
                details[n] = pr_details_from_node(node)
    return details


def fetch_snapshot(repo: str, token: str, since: datetime) -> dict:
    """Return {"repo": ..., "fetched_at": ..., "issues": [...]}."""
    if "/" not in repo:
        raise GitHubError(f"Repository must look like 'owner/name', got {repo!r}.")
    owner, name = repo.split("/", 1)
    client = GitHubClient(token)
    reverts = fetch_reverts(client, owner, name, since)

    issues: List[dict] = []
    cursor = None
    while True:
        data = client.query(ISSUES_QUERY, {"owner": owner, "name": name, "cursor": cursor})
        page = data["repository"]["issues"]
        for node in page["nodes"]:
            issues.append(_issue_from_node(node, reverts))
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    merged = [pr["number"] for issue in issues for pr in issue["linked_prs"] if pr.get("merged_at")]
    details = fetch_pr_details(client, owner, name, merged)
    for issue in issues:
        for pr in issue["linked_prs"]:
            pr.update(details.get(pr["number"], {}))

    return {
        "repo": repo,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
    }


def _issue_from_node(node: dict, reverts: Dict[int, str]) -> dict:
    prs: Dict[int, dict] = {}

    def add_pr(pr: Optional[dict]) -> None:
        if not pr or pr.get("number") is None:
            return
        prs[pr["number"]] = {
            "number": pr["number"],
            "author": _login(pr),
            "merged_at": pr.get("mergedAt"),
            "reverted_at": reverts.get(pr["number"]),
        }

    for pr in node["closedByPullRequestsReferences"]["nodes"]:
        add_pr(pr)

    events = []
    for event in node["timelineItems"]["nodes"]:
        if event["__typename"] == "ClosedEvent":
            closer = event.get("closer") or {}
            if closer.get("__typename") == "PullRequest":
                add_pr(closer)
            reason = event.get("stateReason")
            events.append({
                "type": "closed",
                "at": event["createdAt"],
                "reason": reason.lower() if reason else None,
            })
        elif event["__typename"] == "ReopenedEvent":
            events.append({"type": "reopened", "at": event["createdAt"]})

    return {
        "number": node["number"],
        "title": node["title"],
        "labels": [label["name"] for label in node["labels"]["nodes"]],
        "events": events,
        "linked_prs": sorted(prs.values(), key=lambda p: p["number"]),
    }
