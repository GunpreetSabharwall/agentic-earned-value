"""Turn issue history into AEV work items.

Input is a "snapshot": plain data describing each issue (labels, close and
reopen events, linked pull requests). The snapshot comes either from GitHub
(see github_data.py) or from a JSON file (demo mode and tests). This module
does not talk to GitHub.

Snapshot format for one issue::

    {
      "number": 12,
      "title": "Add login page",
      "labels": ["aev-points:5"],
      "events": [
        {"type": "closed", "at": "2026-01-15T10:00:00Z", "reason": "completed"},
        {"type": "reopened", "at": "2026-01-20T09:00:00Z"}
      ],
      "linked_prs": [
        {"number": 30, "author": "my-agent[bot]",
         "merged_at": "2026-01-15T09:55:00Z", "reverted_at": null}
      ]
    }
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List, Optional, Tuple

POINTS_LABEL = re.compile(r"^\s*aev-points\s*:\s*(\d+(?:\.\d+)?)\s*$", re.IGNORECASE)

AGENT = "A"
HUMAN = "H"
MIXED = "M"
CLASSES = (AGENT, HUMAN, MIXED)


@dataclass
class Episode:
    """One period during which an item was accepted (and maybe clawed back)."""

    accepted_at: datetime
    clawed_back_at: Optional[datetime] = None
    clawback_reason: Optional[str] = None  # "reopened" or "PR #N reverted"

    @property
    def clawed_back(self) -> bool:
        return self.clawed_back_at is not None


@dataclass
class WorkItem:
    number: int
    title: str
    points: Optional[float]
    value: float  # budgeted value BV_i = points x value_per_point
    authorship: Optional[str]  # "A", "H", "M", or None if no merged PR
    episodes: List[Episode] = field(default_factory=list)

    @property
    def gross_ev(self) -> float:
        return self.value * len(self.episodes)

    @property
    def clawback(self) -> float:
        return self.value * sum(1 for e in self.episodes if e.clawed_back)

    @property
    def ev(self) -> float:
        return self.gross_ev - self.clawback


def parse_time(value) -> Optional[datetime]:
    """Parse an ISO date or date-time into a timezone-aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def end_of_day(day: date) -> datetime:
    """The last moment of a calendar day, in UTC."""
    return datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)


def points_from_labels(labels: Iterable[str]) -> Tuple[Optional[float], Optional[str]]:
    """Return (points, warning). Uses the largest value if several labels exist."""
    found = []
    for label in labels:
        match = POINTS_LABEL.match(label or "")
        if match:
            found.append(float(match.group(1)))
    if not found:
        return None, None
    warning = None
    if len(set(found)) > 1:
        warning = f"has several aev-points labels; the largest ({max(found):g}) was used"
    return max(found), warning


def _normalize_login(login: Optional[str]) -> str:
    """'My-Agent[bot]' and 'my-agent' are treated as the same account."""
    text = (login or "ghost").strip().lower()
    if text.endswith("[bot]"):
        text = text[: -len("[bot]")]
    return text


def authorship_class(pr_authors: Iterable[Optional[str]], agent_accounts: Iterable[str]) -> Optional[str]:
    """A if every merged PR is by an agent account, H if none are, M if mixed.

    Returns None when the item has no merged PR (class is unknown).
    """
    agents = {_normalize_login(a) for a in agent_accounts}
    flags = [_normalize_login(a) in agents for a in pr_authors]
    if not flags:
        return None
    if all(flags):
        return AGENT
    if not any(flags):
        return HUMAN
    return MIXED


def _is_completed(reason: Optional[str]) -> bool:
    # Issues closed before GitHub added close reasons have no reason; GitHub
    # treats those as completed, and so do we.
    return reason is None or str(reason).lower() == "completed"


def build_episodes(
    events: List[dict],
    merged_times: List[datetime],
    reverts: List[Tuple[datetime, str]],
    window_days: int,
    as_of: datetime,
) -> List[Episode]:
    """Apply the accept-then-hold rule (method note section 4.3).

    * An item is accepted when it is closed as completed and has at least one
      linked merged PR. The acceptance time is the later of the close and the
      first merge.
    * If it is reopened, or a linked PR is reverted, within ``window_days`` of
      acceptance, the value is clawed back.
    * A clawed-back item can be accepted (and earn) again later.
    * Only events on or before ``as_of`` are considered.
    """
    if not merged_times:
        return []
    first_merge = min(merged_times)
    window = timedelta(days=window_days)

    timeline: List[Tuple[datetime, str, str]] = []
    for event in events:
        at = parse_time(event.get("at"))
        if at is None or at > as_of:
            continue
        kind = event.get("type")
        if kind == "closed" and _is_completed(event.get("reason")):
            timeline.append((max(at, first_merge), "accept", ""))
        elif kind == "reopened":
            timeline.append((at, "undo", "reopened"))
    for at, label in reverts:
        if at <= as_of:
            timeline.append((at, "undo", label))
    timeline.sort(key=lambda entry: entry[0])

    episodes: List[Episode] = []
    current: Optional[Episode] = None
    for at, kind, reason in timeline:
        if kind == "accept":
            if current is None and at <= as_of:
                current = Episode(accepted_at=at)
        elif current is not None and at >= current.accepted_at:
            if at - current.accepted_at <= window:
                current.clawed_back_at = at
                current.clawback_reason = reason
                episodes.append(current)
                current = None
            # An undo after the window does not claw back: value is kept.
    if current is not None:
        episodes.append(current)
    return episodes


def build_work_items(
    snapshot_issues: List[dict],
    value_per_point: float,
    agent_accounts: List[str],
    window_days: int,
    as_of: datetime,
) -> Tuple[List[WorkItem], List[str]]:
    items: List[WorkItem] = []
    warnings: List[str] = []
    for issue in snapshot_issues:
        number = int(issue["number"])
        points, warning = points_from_labels(issue.get("labels", []))
        if warning:
            warnings.append(f"Issue #{number} {warning}.")

        merged_prs = []
        for pr in issue.get("linked_prs", []):
            merged_at = parse_time(pr.get("merged_at"))
            if merged_at is not None and merged_at <= as_of:
                merged_prs.append((pr, merged_at))

        authorship = authorship_class([pr.get("author") for pr, _ in merged_prs], agent_accounts)
        value = float(points or 0) * float(value_per_point)

        episodes: List[Episode] = []
        if points:
            reverts = []
            for pr, _ in merged_prs:
                reverted_at = parse_time(pr.get("reverted_at"))
                if reverted_at is not None:
                    reverts.append((reverted_at, f"PR #{pr.get('number')} reverted"))
            episodes = build_episodes(
                issue.get("events", []),
                [m for _, m in merged_prs],
                reverts,
                window_days,
                as_of,
            )

        items.append(
            WorkItem(
                number=number,
                title=str(issue.get("title", "")),
                points=points,
                value=value,
                authorship=authorship,
                episodes=episodes,
            )
        )
    items.sort(key=lambda i: i.number)
    return items, warnings
