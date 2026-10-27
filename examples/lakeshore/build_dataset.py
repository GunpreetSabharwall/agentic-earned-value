"""Build the Lakeshore Components demo dataset and run AEV on it, week by week.

Lakeshore Components (fictional) is modernizing its Supplier Quality Portal:
$240,000 over 12 weeks, two teams (Portal, Integrations), coding agents open
about two-thirds of pull requests. Week 6 ends on 10 Nov 2026, the day of the
AI Week Great Lakes talk.

Run from the top folder of the repository:

    PYTHONPATH=src python examples/lakeshore/build_dataset.py

It writes, inside examples/lakeshore/:

* .aev/config.yml, .aev/hours.csv, .aev/agent-costs.csv   AEV inputs
* issues.json                 issue history before the on-stage revert
* issues-after-revert.json    the same, after one agent PR (issue #125) is reverted on stage
* results/week-1.json ... week-6.json, week-6-after-revert.json   AEV results
* AEV-REPORT.md, AEV-REPORT-after-revert.md                 week 6 reports

Everything is deterministic: the same script always gives the same files.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from aev import cli  # noqa: E402

REPO = "lakeshore-components/supplier-quality-portal"
START = date(2026, 9, 29)
END = date(2026, 12, 22)
WEEK_ENDS = [START + timedelta(days=7 * n) for n in range(1, 7)]  # Oct 6 ... Nov 10
TALK_DAY = WEEK_ENDS[-1]
LIVE_REVERT_AT = "2026-11-10T15:00:00Z"

PORTAL, INTEG = "pod-portal", "pod-integrations"
DEVS = {PORTAL: ["m-kowalski", "s-reyes"], INTEG: ["d-okafor", "j-chen"]}
COORDINATION_HOURS = [7, 7, 7, 7, 7, 8]  # program meetings etc., no issue number

# Each issue:
# (number, title, team, who, points, accepted, PRs, build h, review h, agent $, extra)
#   who:      "A" agent PRs, "H" human PRs
#   accepted: date the issue was closed as done, or None if still open
#   PRs:      number of merged PRs linked to the issue
#   extra:    {"revert": (pr index, date, reason)} or {"rework_h": (hours, from date)}
ISSUES = [
    # --- Portal: agent-authored, done --------------------------------------
    (101, "Supplier login with single sign-on", PORTAL, "A", 3, "2026-10-02", 2, 22, 3, 330, {}),
    (102, "Supplier profile and certifications page", PORTAL, "A", 2, "2026-10-07", 1, 14, 2, 180, {}),
    (103, "Upload certificate of analysis (PDF)", PORTAL, "A", 3, "2026-10-09", 2, 22, 3, 300, {}),
    (104, "PPAP submission form", PORTAL, "A", 3, "2026-10-14", 2, 24, 4, 340, {}),
    (105, "Corrective action (8D) request list", PORTAL, "A", 2, "2026-10-15", 1, 14, 2, 170, {}),
    (106, "Shipment certificate search and filters", PORTAL, "A", 2, "2026-10-21", 1, 14, 2, 180, {}),
    (107, "Supplier scorecard dashboard", PORTAL, "A", 3, "2026-10-28", 2, 24, 4, 350, {}),
    (108, "Email reminders for overdue 8D responses", PORTAL, "A", 2, "2026-11-04", 1, 14, 2, 150, {}),
    # --- Portal: human-authored, done --------------------------------------
    (109, "Accessibility fixes (WCAG 2.1 AA)", PORTAL, "H", 3, "2026-10-29", 2, 55, 0, 0, {}),
    (110, "Supplier onboarding wizard", PORTAL, "H", 5, "2026-10-16", 3, 90, 0, 0, {}),
    (111, "Role-based access for plant quality engineers", PORTAL, "H", 4, "2026-10-22", 2, 75, 0, 0, {}),
    # --- Integrations: agent-authored, done --------------------------------
    (121, "Nightly sync of supplier master data from ERP", INTEG, "A", 5, "2026-10-08", 2, 16, 18, 420, {}),
    (122, "EDI 856 ship notice parser", INTEG, "A", 4, "2026-10-21", 2, 14, 16, 380, {}),
    (123, "Map ERP defect codes to portal categories", INTEG, "A", 3, "2026-10-09", 1, 12, 22, 360,
     {"revert": (0, "2026-10-16T10:00:00Z", "8Ds routed to the wrong plant"),
      "rework_h": (14, "2026-10-17")}),
    (124, "Sync PPAP approval status back to ERP", INTEG, "A", 3, "2026-10-22", 2, 12, 24, 460,
     {"revert": (1, "2026-10-30T09:00:00Z", "duplicate supplier records in ERP"),
      "rework_h": (16, "2026-10-31")}),
    (125, "Post nonconformance reports (NCR) to ERP", INTEG, "A", 4, "2026-11-03", 2, 14, 20, 520,
     {"live_revert": 1}),
    # --- Integrations: human-authored, done --------------------------------
    (126, "ERP API service account and authentication", INTEG, "H", 4, "2026-10-05", 1, 70, 0, 0, {}),
    (127, "Integration error queue with retry", INTEG, "H", 5, "2026-10-15", 3, 100, 0, 0, {}),
    (128, "EDI 861 receiving advice mapping", INTEG, "H", 3, "2026-10-28", 2, 62, 0, 0, {}),
    # --- Still open (work in progress) -------------------------------------
    (112, "Self-service password reset", PORTAL, "A", 2, None, 1, 10, 2, 150, {}),
    (113, "Bulk upload of inspection results", PORTAL, "A", 5, None, 2, 22, 4, 300, {}),
    (114, "Tablet layout for the plant floor", PORTAL, "A", 3, None, 1, 14, 2, 150, {}),
    (115, "Audit trail export", PORTAL, "H", 3, None, 1, 20, 0, 0, {}),
    (116, "Supplier messaging", PORTAL, "H", 5, None, 0, 0, 0, 0, {}),
    (117, "Spanish and French translations", PORTAL, "H", 5, None, 0, 0, 0, 0, {}),
    (129, "Two-way 8D status sync with ERP", INTEG, "A", 8, None, 2, 14, 20, 620, {}),
    (130, "EDI 810 invoice matching", INTEG, "H", 5, None, 0, 0, 0, 0, {}),
    (131, "Quality hold signal to MES", INTEG, "H", 8, None, 1, 20, 0, 0, {}),
    (132, "Data retention and archiving job", INTEG, "A", 3, None, 1, 6, 8, 260, {}),
    (133, "Supplier master de-duplication", INTEG, "A", 5, None, 1, 8, 12, 380, {}),
    (134, "Cutover rehearsal and data migration", INTEG, "H", 5, None, 1, 15, 0, 0, {}),
]

CONFIG = f"""\
# AEV settings for the Lakeshore Components demo (fictional company).
# Supplier Quality Portal modernization: $240,000 over 12 weeks.

budget_at_completion: 240000
value_per_point: 2000          # 120 points of work in total
start_date: {START.isoformat()}
end_date: {END.isoformat()}
hourly_rate: 100
stabilization_window_days: 14
agent_accounts:
  - coding-agent
agent_label: aev-agent         # agent PRs are opened under a developer's account and labelled

# Same labels as the Program Hub pods, so both tools agree on who is who.
teams:
  Portal: pod-portal
  Integrations: pod-integrations
"""


def day(text: str) -> date:
    return date.fromisoformat(text)


def at(d: date, hour: int) -> str:
    return datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def clamp(d: date) -> date:
    return max(d, START)


def build():
    issues, hours, costs = [], [], []
    live_revert_index = None
    for (number, title, team, who, points, accepted, n_prs, build_h, review_h,
         agent_usd, extra) in ISSUES:
        done = day(accepted) if accepted else None
        # Work in progress: PRs merged in the last week before the talk.
        anchor = done or (TALK_DAY - timedelta(days=3 + number % 4))
        dev = DEVS[team][number % 2]

        prs = []
        for k in range(n_prs):
            merged = anchor - timedelta(days=(n_prs - 1 - k) * 2)
            prs.append({
                "number": None,  # numbered below, in merge order
                "author": dev,
                "merged_at": at(clamp(merged), 14 + k),
                "reverted_at": None,
                "labels": ["aev-agent"] if who == "A" else [],
            })
        if "revert" in extra:
            index, when, _reason = extra["revert"]
            prs[index]["reverted_at"] = when
        if "live_revert" in extra:
            live_revert_index = (len(issues), extra["live_revert"])

        events = [{"type": "closed", "at": at(done, 17), "reason": "completed"}] if done else []
        labels = [f"aev-points:{points}", team, "agent-work" if who == "A" else "human-work"]
        issues.append({"number": number, "title": title, "labels": labels,
                       "events": events, "linked_prs": prs})

        # Costs, spread over the days before the issue was done.
        if build_h:
            first = round(build_h * 0.6, 2)
            hours.append((clamp(anchor - timedelta(days=6)), number, "build", first))
            hours.append((clamp(anchor - timedelta(days=2)), number, "build", round(build_h - first, 2)))
        if review_h:
            hours.append((clamp(anchor - timedelta(days=1)), number, "review", review_h))
        if "rework_h" in extra:
            rework, start = extra["rework_h"]
            hours.append((day(start), number, "build", rework / 2))
            hours.append((day(start) + timedelta(days=2), number, "build", rework / 2))
        if agent_usd:
            when = clamp(anchor - timedelta(days=3))
            model = round(agent_usd * 0.75, 2)
            compute = round(agent_usd * 0.14, 2)
            ci = round(agent_usd - model - compute, 2)
            tokens = int(round(model * 9300, -3))  # about $107 per million tokens, blended
            costs.append((when, number, "model", model, tokens))
            costs.append((when, number, "compute", compute, ""))
            costs.append((when, number, "ci", ci, ""))

    for week, h in zip(WEEK_ENDS, COORDINATION_HOURS):
        hours.append((week - timedelta(days=1), "", "build", h))
    costs.append((date(2026, 10, 1), "", "tools", 200, ""))
    costs.append((date(2026, 11, 1), "", "tools", 200, ""))

    # Number PRs in the order they were merged, as GitHub would.
    all_prs = sorted((pr["merged_at"], issue["number"], pr) for issue in issues for pr in issue["linked_prs"])
    for n, (_, _, pr) in enumerate(all_prs, start=141):
        pr["number"] = n

    hours.sort(key=lambda r: (r[0], str(r[1])))
    costs.sort(key=lambda r: (r[0], str(r[1])))

    after = json.loads(json.dumps(issues))
    i, k = live_revert_index
    after[i]["linked_prs"][k]["reverted_at"] = LIVE_REVERT_AT
    return issues, after, hours, costs


def write_inputs(issues, after, hours, costs):
    aev = HERE / ".aev"
    aev.mkdir(exist_ok=True)
    (aev / "config.yml").write_text(CONFIG, encoding="utf-8")
    with (aev / "hours.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "item", "type", "hours"])
        for d, item, kind, h in hours:
            w.writerow([d.isoformat(), item, kind, f"{h:g}"])
    with (aev / "agent-costs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "item", "category", "amount", "tokens"])
        for d, item, cat, amount, tokens in costs:
            w.writerow([d.isoformat(), item, cat, f"{amount:g}", tokens])
    note = "Lakeshore Components demo (fictional). Same format the AEV tool builds from GitHub."
    for name, data in (("issues.json", issues), ("issues-after-revert.json", after)):
        (HERE / name).write_text(json.dumps({"repo": REPO, "note": note, "issues": data}, indent=2) + "\n",
                                 encoding="utf-8")


def run_aev(snapshot: str, as_of: date, json_out: Path, report: Path = None) -> None:
    scratch = HERE / "results" / ".scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    args = [
        "--config", str(HERE / ".aev" / "config.yml"),
        "--snapshot", str(HERE / snapshot),
        "--repo", REPO,
        "--as-of", as_of.isoformat(),
        "--output", str(report or scratch / "report.md"),
        "--badge", str(scratch / "badge.json"),
        "--json", str(json_out),
    ]
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        assert cli.run(args) == 0


def main():
    issues, after, hours, costs = build()
    write_inputs(issues, after, hours, costs)
    results = HERE / "results"
    results.mkdir(exist_ok=True)
    for n, week_end in enumerate(WEEK_ENDS, start=1):
        last = n == len(WEEK_ENDS)
        run_aev("issues.json", week_end, results / f"week-{n}.json",
                HERE / "AEV-REPORT.md" if last else None)
    run_aev("issues-after-revert.json", TALK_DAY, results / "week-6-after-revert.json",
            HERE / "AEV-REPORT-after-revert.md")
    for f in (results / ".scratch").iterdir():
        f.unlink()
    (results / ".scratch").rmdir()

    for name in [f"week-{n}" for n in range(1, 7)] + ["week-6-after-revert"]:
        d = json.loads((results / f"{name}.json").read_text())
        s, c, i, a = d["summary"], d["classic"], d["indicators"], d["activity"]
        teams = "  ".join(
            f"{t['name'][:5]}:" + ",".join(f"{k}={v['cpi']}" for k, v in t["by_class"].items() if v["ac"])
            for t in d["by_team"])
        print(f"{name:22} PV={s['pv']:>9,.0f} EV={s['ev']:>9,.0f} AC={s['ac']:>9,.0f} "
              f"CPI={s['cpi']} SPI={s['spi']} EAC={s['eac']:,.0f} | classic CPI={c['cpi']} "
              f"SPI={c['spi']} | rework={i['rework_rate']} RLR={i['review_load_ratio']} "
              f"agentPR={a['agent_pr_share']} PRs={a['merged_prs']} tok={a['tokens']:,} | {teams}")


if __name__ == "__main__":
    main()
