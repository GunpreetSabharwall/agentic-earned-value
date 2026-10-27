"""Build the Lakeshore Components demo portfolio: five initiative repos (fictional).

Each initiative tells a different delivery-vs-value story for Program Hub and
AEV. For each one this script writes, under examples/portfolio/<slug>/:

* seed-plan.json        replayed into the empty GitHub repo by scripts/seed_demo.py
* hours.csv, agent-costs.csv   the PMO's cost files (Program Hub: initiatives/<slug>/aev/)
* program-hub-config.yml       the initiative config for Program Hub
* issues-*.json         AEV snapshots: before any demo, after stage slot 1, after its revert
* results/*.json        AEV results for those states, as of the reference date

Run from the top folder of the repository:

    PYTHONPATH=src python examples/portfolio/build_portfolio.py

Every repo follows both requirements pages (docs/REPO-REQUIREMENTS.md here and
in Program-Hub-AI): sized issues, pod labels, PR links (Fixes / Part of), the
aev-agent label plus agent-authored commits, GitHub-style reverts, blocked labels.

Stage slots: each repo holds back three agent PRs. "Prepare stage" merges the
next one the day before a demo; reverting it on stage shows a live clawback.
Three demos per repo before it needs re-seeding.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from aev import cli  # noqa: E402

OWNER = "GunpreetSabharwall"
SEED_DAY = date(2026, 10, 27)        # every cost and merge in the history is on or before this day
REFERENCE_DAY = date(2026, 11, 10)   # the table is computed as of this day (AI Week Great Lakes)
HOURLY_RATE = 100
DEVS = ["a-novak", "b-mensah", "c-ortiz", "d-kim", "e-haddad", "f-lindqvist"]

# Issue rows: (title, pod index, who, points, state, merged PRs, reverted)
#   who:   A agent, H human, M mixed (one agent PR + one human PR)
#   state: done | wip (partial PR merged, still open) | open | blocked | slot (held for a demo)
# Cost model per who: build hours / point, review hours / point, agent $ / point.
INITIATIVES = [
    {
        "slug": "agent-gateway", "name": "Agent Gateway",
        "story": "Internal AI agent platform, mostly agent-written and well tested: agents clearly pay off.",
        "pods": [("pod-platform", "Platform"), ("pod-sdk", "SDK")],
        "start": "2026-09-21", "weeks": 10, "value_per_point": 2000,
        "cost": {"A": (7.5, 2.5, 90), "H": (22.0, 0, 0), "M": (13.0, 1.5, 45)}, "rework_h": 4, "coordination_h": 6,
        "issues": [
            ("Agent gateway API skeleton", 0, "A", 5, "done", 2, False),
            ("Token budget enforcement per team", 0, "A", 5, "done", 2, False),
            ("Model routing by task type", 0, "A", 8, "done", 2, False),
            ("Request and response audit log", 0, "A", 5, "done", 1, False),
            ("Prompt caching layer", 0, "A", 5, "done", 2, False),
            ("Rate limiting and quotas", 0, "H", 5, "done", 2, False),
            ("SSO for the admin console", 0, "H", 3, "done", 1, False),
            ("Python SDK client", 1, "A", 5, "done", 2, False),
            ("TypeScript SDK client", 1, "A", 5, "done", 2, False),
            ("SDK retry and backoff", 1, "A", 3, "done", 1, False),
            ("Usage dashboard per team", 1, "M", 5, "done", 2, False),
            ("Developer docs site", 1, "A", 3, "done", 1, False),
            ("Sample apps: chat and RAG", 1, "A", 5, "done", 2, False),
            ("Cost attribution headers", 0, "A", 3, "slot", 2, False),
            ("Streaming responses in the SDK", 1, "A", 3, "slot", 2, False),
            ("Gateway health checks", 0, "A", 3, "slot", 2, False),
            ("Multi-region failover", 0, "H", 8, "open", 0, False),
            ("Policy engine for PII", 0, "A", 5, "wip", 1, False),
            ("Go SDK client", 1, "A", 3, "open", 0, False),
            ("Load test at 10k requests per second", 0, "H", 3, "open", 0, False),
        ],
    },
    {
        "slug": "cloud-modernization", "name": "Cloud Modernization",
        "story": "Plant and back-office apps moving to cloud, mixed human and agent work: review cost eats the agent savings.",
        "pods": [("pod-migration", "Migration"), ("pod-platform", "Platform")],
        "start": "2026-09-14", "weeks": 16, "value_per_point": 2500,
        "cost": {"A": (8.5, 8.0, 90), "H": (22.0, 0, 0), "M": (13.0, 5.0, 45)}, "rework_h": 10, "coordination_h": 6,
        "issues": [
            ("Inventory of 140 on-prem applications", 0, "H", 5, "done", 1, False),
            ("Landing zone and account structure", 1, "H", 8, "done", 2, False),
            ("Migrate supplier portal to containers", 0, "A", 8, "done", 3, False),
            ("Migrate quality reporting service", 0, "A", 5, "done", 2, False),
            ("Migrate label printing service", 0, "M", 5, "done", 2, False),
            ("Database migration: quality database", 0, "H", 8, "done", 2, False),
            ("Migrate EDI gateway VMs", 0, "A", 5, "done", 2, False),
            ("Migrate shop-floor dashboard", 0, "A", 3, "done", 1, True),
            ("Terraform modules for networking", 1, "A", 5, "done", 2, False),
            ("CI/CD pipelines to cloud", 1, "A", 5, "done", 2, False),
            ("Observability: logs and metrics", 1, "M", 5, "done", 2, False),
            ("Secrets management", 1, "H", 3, "done", 1, False),
            ("Migrate warehouse scanner API", 0, "A", 3, "slot", 2, False),
            ("Autoscaling policies", 1, "A", 3, "slot", 2, False),
            ("Migrate notification service", 0, "A", 3, "slot", 2, False),
            ("Migrate MES connector", 0, "H", 8, "wip", 1, False),
            ("Disaster recovery runbook", 1, "H", 5, "open", 0, False),
            ("Cost tagging and FinOps reports", 1, "A", 5, "wip", 1, False),
            ("Decommission data center racks", 0, "H", 8, "open", 0, False),
            ("Migrate ERP batch jobs", 0, "A", 8, "open", 0, False),
            ("Performance baseline after cutover", 1, "H", 5, "open", 0, False),
            ("Security hardening of clusters", 1, "A", 5, "open", 0, False),
            ("Migrate legacy FTP drop", 0, "A", 5, "open", 0, False),
        ],
    },
    {
        "slug": "data-integration", "name": "Data Integration",
        "story": "ERP and EDI data feeds, agent-heavy with repeated reverts: delivery looks green, value is red.",
        "pods": [("pod-erp", "ERP"), ("pod-edi", "EDI")],
        "start": "2026-09-28", "weeks": 12, "value_per_point": 2000,
        "cost": {"A": (6.0, 7.0, 110), "H": (20.0, 0, 0), "M": (12.0, 5.0, 55)}, "rework_h": 12, "coordination_h": 5,
        "issues": [
            ("Supplier master sync from SAP", 0, "A", 5, "done", 2, False),
            ("Purchase order feed", 0, "A", 5, "done", 2, True),
            ("Goods receipt postings", 0, "A", 3, "done", 1, True),
            ("Quality notification sync", 0, "A", 5, "done", 2, False),
            ("Cost center mapping", 0, "H", 3, "done", 1, False),
            ("Material master delta load", 0, "A", 5, "done", 2, False),
            ("EDI 850 purchase order parser", 1, "A", 5, "done", 2, False),
            ("EDI 856 ship notice parser", 1, "A", 5, "done", 2, False),
            ("EDI 997 acknowledgements", 1, "A", 3, "done", 1, True),
            ("EDI partner onboarding tool", 1, "H", 5, "done", 2, False),
            ("Error queue and replay", 1, "M", 5, "done", 2, False),
            ("EDI 810 invoice parser", 1, "A", 3, "slot", 2, False),
            ("Inventory snapshot feed", 0, "A", 3, "slot", 2, False),
            ("Carrier status updates", 1, "A", 3, "slot", 2, False),
            ("Two-way purchase order change sync", 0, "A", 8, "wip", 1, False),
            ("Data quality dashboard", 0, "H", 5, "open", 0, False),
            ("EDI 940 warehouse order", 1, "A", 5, "open", 0, False),
            ("Partner certification tests", 1, "H", 5, "open", 0, False),
            ("Archive and retention job", 0, "A", 3, "open", 0, False),
            ("Cutover rehearsal", 0, "H", 5, "open", 0, False),
            ("Master data de-duplication", 0, "A", 5, "wip", 1, False),
            ("Monitoring alerts for feeds", 1, "A", 3, "open", 0, False),
        ],
    },
    {
        "slug": "developer-productivity", "name": "Developer Productivity",
        "story": "CI and developer tooling, mostly human, two blockers: late but efficient, a schedule problem not a cost problem.",
        "pods": [("pod-ci", "CI"), ("pod-devex", "DevEx")],
        "start": "2026-09-21", "weeks": 12, "value_per_point": 1500,
        "cost": {"A": (5.0, 1.5, 50), "H": (11.0, 0, 0), "M": (8.0, 1.0, 25)}, "rework_h": 4, "coordination_h": 3,
        "issues": [
            ("Build cache for the monorepo", 0, "H", 8, "done", 2, False),
            ("Flaky test quarantine report", 0, "H", 5, "done", 1, False),
            ("Parallel test runners", 0, "H", 5, "wip", 1, False),
            ("Merge queue rollout", 0, "M", 5, "done", 2, False),
            ("Golden path service template", 1, "H", 8, "done", 2, False),
            ("Local dev containers", 1, "H", 5, "done", 1, False),
            ("AI code review assistant pilot", 1, "A", 5, "done", 2, False),
            ("Onboarding guide refresh", 1, "A", 3, "done", 1, False),
            ("CI pipeline lint rules", 0, "A", 3, "done", 1, False),
            ("Dependency update bot", 0, "A", 3, "slot", 2, False),
            ("Pull request size linter", 0, "A", 3, "slot", 2, False),
            ("Docs search", 1, "A", 3, "slot", 2, False),
            ("Remote build execution", 0, "H", 8, "blocked", 0, False),
            ("Self-service preview environments", 1, "H", 8, "blocked", 0, False),
            ("Test impact analysis", 0, "H", 5, "wip", 1, False),
            ("Developer portal", 1, "H", 8, "open", 0, False),
            ("Inner-source catalog", 1, "H", 3, "open", 0, False),
            ("Build time SLOs", 0, "A", 3, "open", 0, False),
        ],
    },
    {
        "slug": "security-automation", "name": "Security Automation",
        "story": "Scanning and policy automation with three blockers: delivery risk that cost metrics alone would miss.",
        "pods": [("pod-appsec", "AppSec"), ("pod-cloudsec", "CloudSec")],
        "start": "2026-10-05", "weeks": 14, "value_per_point": 2000,
        "cost": {"A": (5.0, 2.5, 70), "H": (17.0, 0, 0), "M": (10.0, 1.5, 35)}, "rework_h": 4, "coordination_h": 4,
        "issues": [
            ("SAST in every pipeline", 0, "A", 5, "done", 2, False),
            ("Secret scanning with push protection", 0, "H", 3, "done", 1, False),
            ("Dependency vulnerability SLA report", 0, "A", 5, "done", 2, False),
            ("Cloud posture baseline (CIS)", 1, "A", 5, "done", 2, False),
            ("IAM least-privilege review", 1, "H", 5, "done", 1, False),
            ("Guardrail policies as code", 1, "M", 5, "done", 2, False),
            ("Container image signing", 0, "A", 3, "slot", 2, False),
            ("SBOM for every release", 0, "A", 3, "slot", 2, False),
            ("Alert routing to owners", 1, "A", 3, "slot", 2, False),
            ("Pen test remediation tracker", 0, "H", 5, "blocked", 0, False),
            ("Network segmentation for plant OT", 1, "H", 8, "blocked", 0, False),
            ("Vendor access reviews", 1, "H", 5, "blocked", 0, False),
            ("Threat model templates", 0, "H", 3, "open", 0, False),
            ("DAST for public apps", 0, "A", 5, "wip", 1, False),
            ("Key rotation automation", 1, "A", 5, "open", 0, False),
            ("Incident runbooks", 1, "H", 5, "open", 0, False),
            ("Security champions training", 0, "H", 3, "open", 0, False),
            ("Central logging to the SIEM", 1, "A", 5, "open", 0, False),
            ("WAF rules for the supplier portal", 0, "A", 3, "open", 0, False),
        ],
    },
]

REVERT_REASONS = ["data loaded twice into the ERP", "wrong unit of measure in postings",
                  "acknowledgements sent to the wrong partner", "dashboard showed stale plant data"]


def at(d: date, hour: int) -> str:
    return datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(text: str) -> str:
    return "-".join("".join(c if c.isalnum() else " " for c in text.lower()).split()[:6])


def build(spec: dict):
    start = date.fromisoformat(spec["start"])
    end = start + timedelta(weeks=spec["weeks"])
    pods = spec["pods"]
    rows = spec["issues"]
    done_rows = [i for i, r in enumerate(rows) if r[4] == "done"]
    last_done = SEED_DAY - timedelta(days=1)
    first_done = min(start + timedelta(days=6), last_done)
    span = max((last_done - first_done).days, 1)

    issues, hours, costs, timeline = [], [], [], []
    slot_no = 0
    revert_no = 0
    for n, (title, pod, who, points, state, n_prs, reverted) in enumerate(rows, start=1):
        dev = DEVS[n % len(DEVS)]
        if state == "done":
            k = done_rows.index(n - 1)
            accepted = first_done + timedelta(days=round(span * (k + 1) / (len(done_rows) + 1)))
        else:
            accepted = None
        anchor = accepted or (SEED_DAY - timedelta(days=2 + n % 4))
        labels = [f"aev-points:{points}", pods[pod][0],
                  {"A": "agent-work", "H": "human-work", "M": "mixed-work"}[who]]
        if state == "blocked":
            labels.append("blocked")
        prs = []
        for j in range(n_prs):
            agent = who == "A" or (who == "M" and j == 0)
            merged = max(anchor - timedelta(days=(n_prs - 1 - j) * 2), start)
            last = j == n_prs - 1
            hold = state == "slot" and last
            prs.append({"number": None, "author": dev, "merged_at": None if hold else at(merged, 14 + j),
                        "reverted_at": None, "labels": ["aev-agent"] if agent else [],
                        "_agent": agent, "_link": "fixes" if (state in ("done", "slot") and last) else "part_of",
                        "_hold": hold, "_order": at(merged, 14 + j), "_part": (j + 1, n_prs)})
        slot = None
        if state == "slot":
            slot_no += 1
            slot = slot_no
        if reverted:
            prs[-1]["_revert_at"] = at(accepted + timedelta(days=3), 10)
            prs[-1]["_revert_reason"] = REVERT_REASONS[revert_no % len(REVERT_REASONS)]
            revert_no += 1
        events = [{"type": "closed", "at": at(accepted, 17), "reason": "completed"}] if accepted else []
        issues.append({"number": n, "title": title, "labels": labels, "events": events, "linked_prs": prs,
                       "_slot": slot, "_state": state, "_pod": pod})

        # Costs. Done and slot items carry full cost; work in progress half; blocked a little.
        share = {"done": 1.0, "slot": 1.0, "wip": 0.5, "blocked": 0.25, "open": 0.0}[state]
        if share:
            bh, rh, au = spec["cost"][who]
            build_h = round(points * bh * share, 1)
            review_h = round(points * rh * share, 1)
            agent_usd = round(points * au * share, 2)
            day = max(min(anchor, SEED_DAY) - timedelta(days=3), start)
            if build_h:
                hours.append((day, n, "build", build_h))
            if review_h:
                hours.append((max(min(anchor, SEED_DAY) - timedelta(days=1), start), n, "review", review_h))
            if agent_usd:
                model = round(agent_usd * 0.78, 2)
                costs.append((day, n, "model", model, int(round(model * 9000, -3))))
                costs.append((day, n, "ci", round(agent_usd - model, 2), ""))
            if reverted:
                hours.append((min(accepted + timedelta(days=4), SEED_DAY), n, "build", points * spec["rework_h"] / 5))
    week = start + timedelta(days=6)
    while week <= SEED_DAY:
        hours.append((week, "", "build", spec["coordination_h"]))
        week += timedelta(days=7)
    costs.append((start, "", "tools", 150, ""))

    # Number PRs as GitHub will: issues first (1..N), then PRs and reverts in creation order.
    events = []
    for issue in issues:
        for pr in issue["linked_prs"]:
            events.append((pr["_order"], 0, issue["number"], "pr", pr))
            if pr.get("_revert_at"):
                events.append((pr["_revert_at"], 1, issue["number"], "revert", pr))
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    plan = []
    for issue in issues:
        plan.append({"step": "issue", "number": issue["number"], "title": issue["title"], "labels": issue["labels"],
                     "body": (f"Team: {pods[issue['_pod']][1]}. Size: {issue['labels'][0].split(':')[1]} points. "
                              f"{spec['name']} initiative, Lakeshore Components (fictional demo).")})
    number = len(issues) + 1
    for when, _, issue_no, kind, pr in events:
        issue = issues[issue_no - 1]
        if kind == "pr":
            pr["number"] = number
            k, total = pr["_part"]
            area = slugify(spec["pods"][issue["_pod"]][1])
            plan.append({"step": "pr", "number": number, "issue": issue_no,
                         "title": issue["title"] + (f" (part {k} of {total})" if total > 1 else ""),
                         "link": pr["_link"], "agent": pr["_agent"], "developer": pr["author"],
                         "path": f"src/{area}/{slugify(issue['title'])}/part-{k}.md",
                         "hold": pr["_hold"], "slot": issue["_slot"] if pr["_hold"] else None,
                         "planned_merge": when})
        else:
            pr["reverted_at"] = pr["_revert_at"]
            plan.append({"step": "revert", "number": number, "reverts": pr["number"], "issue": issue_no,
                         "reason": pr["_revert_reason"], "planned_merge": when})
        number += 1
    return start, end, issues, hours, costs, plan


def snapshot(issues, state: str):
    """AEV snapshot: 'before' (no slot merged), 'slot1' (slot 1 merged), 'slot1-reverted'."""
    out = []
    for issue in issues:
        i = {k: v for k, v in issue.items() if not k.startswith("_")}
        i["events"] = list(issue["events"])
        prs = []
        for pr in issue["linked_prs"]:
            p = {k: v for k, v in pr.items() if not k.startswith("_")}
            if pr["_hold"]:
                if issue["_slot"] == 1 and state != "before":
                    p["merged_at"] = at(REFERENCE_DAY - timedelta(days=1), 15)
                    i["events"] = [{"type": "closed", "at": at(REFERENCE_DAY - timedelta(days=1), 15), "reason": "completed"}]
                    if state == "slot1-reverted":
                        p["reverted_at"] = at(REFERENCE_DAY, 15)
                else:
                    continue  # held PR not merged yet: not linked as merged work
            prs.append(p)
        i["linked_prs"] = prs
        out.append(i)
    return out


def config_yml(spec, start, end) -> str:
    pods = "\n".join(f"  - slug: {slugify(name)}\n    label: {label}\n    name: {name}" for label, name in spec["pods"])
    return f"""# {spec['name']}: Lakeshore Components demo portfolio (fictional company).
# Story: {spec['story']}
name: {spec['name']}
slug: {spec['slug']}
source_repo: {OWNER}/initiative-{spec['slug']}
source_repo_url: https://github.com/{OWNER}/initiative-{spec['slug']}
owner: "@{OWNER}"
status: active
week_start: {start.isoformat()}
duration_weeks: {spec['weeks']}
showcase_date: {end.isoformat()}
github_project_id: ""
labels:
  blocked: blocked
  dependency: dependency
  adr: adr-required
sync_cadence: weekly
pods:
{pods}
# Value signal (Feature 22): Program Hub runs AEV on source_repo. Costs are in aev/.
aev:
  enabled: true
  mode: hub
  budget_at_completion: {sum(r[3] for r in spec['issues']) * spec['value_per_point']}
  value_per_point: {spec['value_per_point']}
  hourly_rate: {HOURLY_RATE}
  stabilization_window_days: 14
  agent_accounts:
    - coding-agent
  agent_label: aev-agent
"""


def aev_config(spec, start, end) -> str:
    teams = "\n".join(f"  {name}: {label}" for label, name in spec["pods"])
    return (f"budget_at_completion: {sum(r[3] for r in spec['issues']) * spec['value_per_point']}\n"
            f"value_per_point: {spec['value_per_point']}\nstart_date: {start.isoformat()}\nend_date: {end.isoformat()}\n"
            f"hourly_rate: {HOURLY_RATE}\nstabilization_window_days: 14\nagent_accounts:\n  - coding-agent\n"
            f"agent_label: aev-agent\nteams:\n{teams}\n")


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for row in sorted(rows, key=lambda r: (r[0], str(r[1]))):
            w.writerow([row[0].isoformat()] + [f"{x:g}" if isinstance(x, float) else x for x in row[1:]])


def run_aev(folder: Path, snap: str, out: Path):
    scratch = folder / ".scratch"
    scratch.mkdir(exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        code = cli.run(["--config", str(scratch / "config.yml"), "--hours", str(folder / "hours.csv"),
                        "--agent-costs", str(folder / "agent-costs.csv"), "--snapshot", str(folder / snap),
                        "--as-of", REFERENCE_DAY.isoformat(), "--repo", folder.name,
                        "--output", str(scratch / "r.md"), "--badge", str(scratch / "b.json"), "--json", str(out)])
    assert code == 0


def main():
    table = []
    for spec in INITIATIVES:
        folder = HERE / spec["slug"]
        (folder / "results").mkdir(parents=True, exist_ok=True)
        start, end, issues, hours, costs, plan = build(spec)
        (folder / "seed-plan.json").write_text(json.dumps({
            "repo_note": "Replay into an EMPTY GitHub repo; numbers then match this dataset.",
            "initiative": spec["name"], "story": spec["story"],
            "slots": sorted(({"slot": s["slot"], "pr": s["number"], "issue": s["issue"]}
                             for s in plan if s["step"] == "pr" and s["hold"]), key=lambda x: x["slot"]),
            "steps": plan}, indent=2) + "\n", encoding="utf-8")
        write_csv(folder / "hours.csv", ["date", "item", "type", "hours"], hours)
        write_csv(folder / "agent-costs.csv", ["date", "item", "category", "amount", "tokens"], costs)
        (folder / "program-hub-config.yml").write_text(config_yml(spec, start, end), encoding="utf-8")
        scratch = folder / ".scratch"
        scratch.mkdir(exist_ok=True)
        (scratch / "config.yml").write_text(aev_config(spec, start, end), encoding="utf-8")
        for state in ("before", "slot1", "slot1-reverted"):
            name = f"issues-{state}.json"
            (folder / name).write_text(json.dumps({"repo": f"{OWNER}/initiative-{spec['slug']}",
                                                   "issues": snapshot(issues, state)}, indent=2) + "\n", encoding="utf-8")
            run_aev(folder, name, folder / "results" / f"{state}.json")
        for f in scratch.iterdir():
            f.unlink()
        scratch.rmdir()
        r = {s: json.loads((folder / "results" / f"{s}.json").read_text()) for s in ("before", "slot1", "slot1-reverted")}
        blocked = sum(1 for i in issues if i["_state"] == "blocked")
        table.append((spec, r, blocked, len(issues), sum(1 for s in plan if s["step"] != "issue")))
    print_table(table)


def print_table(table):
    def h(health):
        return {"brightgreen": "Green", "yellow": "Amber", "red": "Red"}.get(health, health)
    print(f"Computed as of {REFERENCE_DAY} (no stage slot used yet), then after slot 1 is staged and reverted.\n")
    for spec, r, blocked, n_issues, n_prs in table:
        b, s1, rv = r["before"], r["slot1"], r["slot1-reverted"]
        sm, cl, ind, act = b["summary"], b["classic"], b["indicators"], b["activity"]
        delivery = "Green" if blocked == 0 else ("Amber" if blocked <= 2 else "Red")
        teams = "; ".join(f"{t['name']} " + "/".join(f"{k}={v['cpi']:.2f}" for k, v in t["by_class"].items()
                                                        if v["ac"] and k != "Unassigned" and v["cpi"] is not None)
                          for t in b["by_team"] if t["name"] != "No team")
        print(f"{spec['name']}: {n_issues} issues, {n_prs} PRs+reverts, BAC ${sm['bac']:,.0f}, blockers {blocked} "
              f"→ delivery {delivery}")
        print(f"   value {h(sm['health'])}: CPI {sm['cpi']:.2f} (classic {cl['cpi']:.2f}), SPI {sm['spi']:.2f}, "
              f"rework {ind['rework_rate']*100:.1f}%, EAC ${sm['eac']:,.0f}, agent PRs {act['agent_pr_share']*100:.0f}%")
        print(f"   teams: {teams}")
        print(f"   demo slot 1: CPI {s1['summary']['cpi']:.2f} ({h(s1['summary']['health'])}) → after revert "
              f"{rv['summary']['cpi']:.2f} ({h(rv['summary']['health'])})")


if __name__ == "__main__":
    main()
