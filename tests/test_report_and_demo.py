"""Report text, badge, demo mode and GitHub data mapping."""

import json
from datetime import date

from aev import cli
from aev.calculator import compute
from aev.config import parse_config
from aev.github_data import REVERT_BODY, _issue_from_node
from aev.report import badge_color, money, percent, ratio, render_badge, render_report, what_this_means

CONFIG = parse_config({
    "budget_at_completion": 1000, "value_per_point": 10, "start_date": "2026-01-01",
    "end_date": "2026-02-01", "hourly_rate": 50,
})


def test_formatting_helpers_show_na():
    assert money(None) == ratio(None) == percent(None) == "n/a"
    assert money(66666.67) == "$66,667"
    assert money(-5) == "-$5"
    assert ratio(0.714) == "0.71"
    assert percent(0.1111) == "11.1%"


def test_badge_colors():
    assert badge_color(None) == "lightgrey"
    assert badge_color(1.0) == "brightgreen"
    assert badge_color(0.95) == "yellow"
    assert badge_color(0.5) == "red"


def test_empty_report_renders_with_na():
    r = compute(CONFIG, date(2026, 1, 1), [], [], [])
    text = render_report(r, CONFIG)
    assert "n/a" in text
    assert "None. No accepted item" in text
    badge = json.loads(render_badge(r))
    assert badge == {"schemaVersion": 1, "label": "AEV CPI", "message": "n/a", "color": "lightgrey"}
    assert "cannot be measured" in what_this_means(r)


def run_demo_inputs(tmp_path):
    """Run on the demo inputs, writing outputs to a temp folder (repo untouched)."""
    out, badge = tmp_path / "report.md", tmp_path / "badge.json"
    demo = cli.DEMO_DIR
    code = cli.run([
        "--config", str(demo / ".aev" / "config.yml"),
        "--snapshot", str(demo / "issues.json"),
        "--repo", "example/demo-project",
        "--output", str(out),
        "--badge", str(badge),
    ])
    assert code == 0
    return out.read_text(encoding="utf-8"), badge.read_text(encoding="utf-8")


def test_demo_data_reproduces_worked_example(tmp_path):
    text, badge = run_demo_inputs(tmp_path)
    for expected in [
        "| CPI = EV / AC | 1.00 |",
        "| SPI = EV / PV | 0.80 |",
        "| EAC = AC + (BAC − EV) / CPI | $100,000 |",
        "| Rework Rate | Clawback / Gross EV | 11.1% |",
        "| Agent Cost Share | AC_agent / AC | 10.0% |",
        "| Review Load Ratio | AC_review / AC_agent | 1.50 |",
        "| Agent-authored (A) | 2 | $20,000 | $12,000 | 1.67 |",
        "| Human-authored (H) | 2 | $20,000 | $28,000 | 0.71 |",
        "| CPI | 1.50 | 1.00 |",
        "| #3 | Fix date parsing in import | $3,000 |",
        "| #4 | Add search filters | $2,000 |",
        "**What this means:**",
    ]:
        assert expected in text, expected
    assert json.loads(badge)["message"] == "1.00"


def test_committed_demo_outputs_are_up_to_date(tmp_path):
    """examples/demo/ outputs must match what `python -m aev --demo` produces."""
    text, badge = run_demo_inputs(tmp_path)
    demo = cli.DEMO_DIR
    assert (demo / "AEV-REPORT.md").read_text(encoding="utf-8") == text
    assert (demo / ".aev" / "badge.json").read_text(encoding="utf-8") == badge


def test_bad_config_returns_error_code(tmp_path):
    bad = tmp_path / "config.yml"
    bad.write_text("budget_at_completion: 10\n", encoding="utf-8")
    assert cli.run(["--config", str(bad), "--snapshot", "unused.json"]) == 2


# --- GitHub data mapping (no network) ------------------------------------------------

def test_revert_body_pattern():
    match = REVERT_BODY.search("Reverts some-owner/some.repo#42\n\nBecause it broke things")
    assert match and match.group(1) == "42"


def test_issue_from_graphql_node():
    node = {
        "number": 5,
        "title": "Do the thing",
        "labels": {"nodes": [{"name": "aev-points:3"}]},
        "closedByPullRequestsReferences": {"nodes": [
            {"number": 20, "mergedAt": "2026-01-02T00:00:00Z", "author": {"login": "bot"}},
        ]},
        "timelineItems": {"nodes": [
            {"__typename": "ClosedEvent", "createdAt": "2026-01-02T00:01:00Z",
             "stateReason": "COMPLETED",
             "closer": {"__typename": "PullRequest", "number": 21,
                        "mergedAt": "2026-01-02T00:00:30Z", "author": None}},
            {"__typename": "ReopenedEvent", "createdAt": "2026-01-03T00:00:00Z"},
        ]},
    }
    issue = _issue_from_node(node, reverts={20: "2026-01-04T00:00:00Z"})
    assert issue["labels"] == ["aev-points:3"]
    assert issue["events"] == [
        {"type": "closed", "at": "2026-01-02T00:01:00Z", "reason": "completed"},
        {"type": "reopened", "at": "2026-01-03T00:00:00Z"},
    ]
    assert issue["linked_prs"] == [
        {"number": 20, "author": "bot", "merged_at": "2026-01-02T00:00:00Z",
         "reverted_at": "2026-01-04T00:00:00Z"},
        {"number": 21, "author": None, "merged_at": "2026-01-02T00:00:30Z", "reverted_at": None},
    ]


def test_what_this_means_variants():
    from aev.costs import HoursEntry
    # Costs but no value: CPI 0 -> over budget; PV > 0 -> behind schedule.
    r = compute(CONFIG, date(2026, 1, 15), [], [HoursEntry(date(2026, 1, 2), None, "build", 1)], [])
    assert what_this_means(r) == (
        "For every $1 spent, the project has earned $0.00 of value; "
        "it is over budget and behind schedule."
    )
    # Nothing spent, but work was planned by now.
    r = compute(CONFIG, date(2026, 1, 15), [], [], [])
    assert what_this_means(r) == (
        "No cost has been recorded yet, so cost efficiency cannot be measured; "
        "it is behind schedule."
    )
    # Before the start: nothing planned, nothing spent.
    r = compute(CONFIG, date(2026, 1, 1), [], [], [])
    assert what_this_means(r).endswith("and no work was planned to be done yet.")


def test_pr_details_query_and_mapping():
    from aev.github_data import pr_details_from_node, pr_details_query

    query = pr_details_query([7, 12])
    assert "pr7: pullRequest(number: 7)" in query and "pr12: pullRequest(number: 12)" in query
    assert "authors(first: 10)" in query

    node = {
        "number": 7,
        "labels": {"nodes": [{"name": "aev-agent"}]},
        "commits": {"totalCount": 3, "nodes": [
            {"commit": {"authors": {"nodes": [
                {"name": "Claude", "email": "noreply@example.com", "user": {"login": "claude"}},
                {"name": "Jane", "email": "jane@example.com", "user": None},
            ]}}},
        ]},
    }
    assert pr_details_from_node(node) == {
        "labels": ["aev-agent"],
        "commits": [{"authors": [
            {"login": "claude", "name": "Claude", "email": "noreply@example.com"},
            {"login": None, "name": "Jane", "email": "jane@example.com"},
        ]}],
        "commits_truncated": True,
    }
