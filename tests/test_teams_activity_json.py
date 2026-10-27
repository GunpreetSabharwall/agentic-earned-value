"""v0.4.0: breakdown by team, activity numbers, tokens column and JSON output."""

import json
from pathlib import Path
from datetime import date, datetime, timezone

import pytest

from aev.calculator import NO_TEAM, compute
from aev.config import ConfigError, parse_config
from aev.costs import AgentCostEntry, HoursEntry, load_agent_costs
from aev.export import SCHEMA, results_to_dict
from aev.items import Episode, WorkItem, build_work_items
from aev.report import render_report

AS_OF = date(2026, 2, 9)
T = datetime(2026, 1, 20, tzinfo=timezone.utc)


def config(**overrides):
    raw = {
        "budget_at_completion": 100000, "value_per_point": 1000,
        "start_date": "2026-01-05", "end_date": "2026-03-16", "hourly_rate": 100,
        "teams": {"Portal": "pod-portal", "Integrations": "pod-integrations"},
    }
    raw.update(overrides)
    return parse_config(raw)


def item(number, value, cls, labels, clawed=False, prs=None):
    ep = Episode(accepted_at=T, clawed_back_at=T if clawed else None,
                 clawback_reason="reopened" if clawed else None)
    return WorkItem(number=number, title=f"Item {number}", points=value / 1000, value=value,
                    authorship=cls, episodes=[ep], labels=labels,
                    merged_prs=prs if prs is not None else [{"number": number + 100, "class": cls, "merged_at": T}])


def sample():
    items = [
        item(1, 5000, "A", ["pod-portal"]),
        item(2, 3000, "H", ["POD-Portal", "feature"]),
        item(3, 4000, "A", ["pod-integrations"], clawed=True),
        item(4, 2000, "H", []),  # no team label
    ]
    hours = [
        HoursEntry(AS_OF, 1, "review", 10), HoursEntry(AS_OF, 2, "build", 30),
        HoursEntry(AS_OF, 3, "review", 20), HoursEntry(AS_OF, None, "build", 5),
    ]
    costs = [AgentCostEntry(AS_OF, 1, "model", 500, tokens=2_000_000),
             AgentCostEntry(AS_OF, 3, "model", 700, tokens=3_000_000)]
    return items, hours, costs


def test_teams_config_parsing():
    assert config().teams == {"Portal": "pod-portal", "Integrations": "pod-integrations"}
    assert parse_config({**config_raw(), "teams": None}).teams == {}
    with pytest.raises(ConfigError):
        parse_config({**config_raw(), "teams": ["pod-portal"]})


def config_raw():
    return {"budget_at_completion": 1, "value_per_point": 1, "start_date": "2026-01-01",
            "end_date": "2026-02-01", "hourly_rate": 1}


def test_breakdown_by_team_and_class():
    items, hours, costs = sample()
    r = compute(config(), AS_OF, items, hours, costs)
    portal, integ, none = r.by_team["Portal"], r.by_team["Integrations"], r.by_team[NO_TEAM]
    # Portal: agent item 1 (EV 5000, AC 1000 review + 500 agent), human item 2 (case-insensitive label)
    assert portal.by_class["A"].ev == 5000 and portal.by_class["A"].ac == 1500
    assert portal.by_class["H"].ev == 3000 and portal.by_class["H"].ac == 3000
    assert portal.ev == 8000 and portal.items_accepted == 2
    # Integrations: clawed back, so no EV, but the cost stays
    assert integ.ev == 0 and integ.ac == 2700 and integ.cpi == 0
    # Item 4 and the cost row with no item land in "No team"
    assert none.by_class["H"].ev == 2000 and none.by_class["Unassigned"].ac == 500
    # Team totals add up to the program totals
    assert sum(t.ev for t in r.by_team.values()) == r.ev
    assert sum(t.ac for t in r.by_team.values()) == pytest.approx(r.ac)


def test_no_team_row_dropped_when_empty_and_no_teams_means_no_breakdown():
    items, hours, costs = sample()
    r = compute(config(), AS_OF, items[:3], hours[:3], costs)
    assert NO_TEAM not in r.by_team
    r = compute(config(teams=None), AS_OF, items, hours, costs)
    assert r.by_team == {}
    assert "## By team" not in render_report(r, config(teams=None))


def test_activity_counts():
    items, hours, costs = sample()
    shared = {"number": 999, "class": "A", "merged_at": T}  # one PR linked to two issues
    items[0].merged_prs.append(shared)
    items[1].merged_prs.append(dict(shared))
    items.append(item(5, 1000, "M", [], prs=[{"number": 105, "class": "M", "merged_at": T}]))
    items[-1].episodes = []  # merged but not closed yet
    a = compute(config(), AS_OF, items, hours, costs).activity
    assert a.merged_prs == 6  # 101-104, 105, 999 counted once
    assert (a.agent_prs, a.mixed_prs, a.human_prs) == (3, 1, 2)
    assert a.agent_pr_share == 0.5 and a.ai_assisted_pr_share == pytest.approx(4 / 6)
    assert a.items_closed == 4
    assert a.agent_spend == 1200 and a.tokens == 5_000_000


def test_pr_classes_recorded_on_items():
    issues = [{"number": 1, "title": "x", "labels": ["aev-points:1", "pod-portal"],
               "events": [{"type": "closed", "at": "2026-01-10T00:00:00Z"}],
               "linked_prs": [{"number": 7, "author": "bot", "merged_at": "2026-01-10T00:00:00Z"},
                              {"number": 8, "author": "jane", "merged_at": "2026-01-11T00:00:00Z"},
                              {"number": 9, "author": "bot", "merged_at": None}]}]
    items, _ = build_work_items(issues, 1000, ["bot"], 14, T.replace(month=2))
    assert [p["class"] for p in items[0].merged_prs] == ["A", "H"]
    assert items[0].labels == ["aev-points:1", "pod-portal"]


def test_tokens_column_is_optional(tmp_path):
    path = tmp_path / "agent-costs.csv"
    path.write_text("date,item,category,amount,tokens\n2026-01-10,1,model,10,1500000\n"
                    "2026-01-11,,ci,2,\n2026-01-12,,model,1,-5\n", encoding="utf-8")
    entries, warnings = load_agent_costs(path)
    assert [e.tokens for e in entries] == [1_500_000, 0]
    assert len(warnings) == 1 and "tokens cannot be negative" in warnings[0]


def test_report_and_json_include_new_sections():
    items, hours, costs = sample()
    cfg = config()
    r = compute(cfg, AS_OF, items, hours, costs)
    text = render_report(r, cfg)
    assert "## AI activity vs. value" in text and "## By team" in text
    assert "| Agent spend | $1,200 (5.0M tokens) |" in text
    assert "| **Portal total** | | **2** | **$8,000** | **$4,500** | **1.78** |" in text

    data = json.loads(json.dumps(results_to_dict(r, cfg, repo="o/r")))
    assert data["schema"] == SCHEMA and data["repo"] == "o/r" and data["as_of"] == "2026-02-09"
    assert data["summary"]["ev"] == r.ev and data["summary"]["health"] in {"red", "yellow", "brightgreen"}
    assert [t["name"] for t in data["by_team"]] == ["Portal", "Integrations", NO_TEAM]
    assert data["activity"]["tokens"] == 5_000_000 and data["activity"]["items_that_stuck"] == 3
    item3 = next(i for i in data["items"] if i["number"] == 3)
    assert item3["team"] == "Integrations" and item3["episodes"][0]["reason"] == "reopened"
    assert item3["episodes"][0]["accepted_at"] == "2026-01-20T00:00:00Z"


# --- Lakeshore demo dataset (examples/lakeshore) -----------------------------

LAKESHORE = Path(__file__).resolve().parents[1] / "examples" / "lakeshore"


def run_lakeshore(tmp_path, snapshot):
    from aev import cli
    out = tmp_path / "aev.json"
    code = cli.run(["--config", str(LAKESHORE / ".aev" / "config.yml"),
                    "--snapshot", str(LAKESHORE / snapshot), "--as-of", "2026-11-10",
                    "--repo", "lakeshore-components/supplier-quality-portal",
                    "--output", str(tmp_path / "r.md"), "--badge", str(tmp_path / "b.json"),
                    "--json", str(out)])
    assert code == 0
    return out.read_text(encoding="utf-8")


@pytest.mark.parametrize("snapshot,result", [
    ("issues.json", "week-6.json"),
    ("issues-after-revert.json", "week-6-after-revert.json"),
])
def test_lakeshore_committed_results_are_up_to_date(tmp_path, snapshot, result):
    assert run_lakeshore(tmp_path, snapshot) == (LAKESHORE / "results" / result).read_text(encoding="utf-8")


def test_lakeshore_tells_the_talk_story(tmp_path):
    before = json.loads(run_lakeshore(tmp_path, "issues.json"))
    after = json.loads(run_lakeshore(tmp_path, "issues-after-revert.json"))
    # Classic EVM looks great and does not move when work is reverted.
    assert before["classic"] == after["classic"]
    assert after["classic"]["cpi"] == pytest.approx(1.45, abs=0.005)
    # The on-stage revert turns the badge from green to yellow.
    assert (before["summary"]["health"], after["summary"]["health"]) == ("brightgreen", "yellow")
    assert after["summary"]["cpi"] == pytest.approx(0.96, abs=0.005)
    assert after["summary"]["spi"] == pytest.approx(0.88, abs=0.005)
    teams = {t["name"]: t["by_class"] for t in after["by_team"]}
    assert teams["Portal"]["A"]["cpi"] == pytest.approx(1.6)
    assert teams["Integrations"]["A"]["cpi"] == pytest.approx(0.6)
    assert after["activity"]["agent_pr_share"] == pytest.approx(0.644, abs=0.001)


def test_cost_files_can_live_anywhere(tmp_path):
    """Central mode: settings and cost files outside the measured repo."""
    from aev import cli
    settings, costs = tmp_path / "settings", tmp_path / "costs"
    settings.mkdir(); costs.mkdir()
    (settings / "config.yml").write_text((LAKESHORE / ".aev" / "config.yml").read_text(), encoding="utf-8")
    (costs / "h.csv").write_text((LAKESHORE / ".aev" / "hours.csv").read_text(), encoding="utf-8")
    (costs / "a.csv").write_text((LAKESHORE / ".aev" / "agent-costs.csv").read_text(), encoding="utf-8")
    out = tmp_path / "aev.json"
    code = cli.run(["--config", str(settings / "config.yml"), "--hours", str(costs / "h.csv"),
                    "--agent-costs", str(costs / "a.csv"), "--snapshot", str(LAKESHORE / "issues-after-revert.json"),
                    "--as-of", "2026-11-10", "--repo", "lakeshore-components/supplier-quality-portal",
                    "--output", str(tmp_path / "r.md"), "--badge", str(tmp_path / "b.json"), "--json", str(out)])
    assert code == 0
    assert out.read_text(encoding="utf-8") == (LAKESHORE / "results" / "week-6-after-revert.json").read_text(encoding="utf-8")
