"""End-to-end calculation, including the method note's worked example."""

from datetime import date, datetime, timezone

import pytest

from aev.calculator import UNASSIGNED, compute
from aev.config import parse_config
from aev.costs import AgentCostEntry, HoursEntry
from aev.items import Episode, WorkItem

AS_OF = date(2026, 2, 9)


def config(**overrides):
    raw = {
        "budget_at_completion": 100000,
        "value_per_point": 1000,
        "start_date": "2026-01-05",
        "end_date": "2026-03-16",
        "hourly_rate": 100,
        "agent_accounts": ["bot"],
    }
    raw.update(overrides)
    return parse_config(raw)


def accepted(day):
    return Episode(accepted_at=datetime(2026, 1, day, tzinfo=timezone.utc))


def clawed(day, back_day):
    return Episode(
        accepted_at=datetime(2026, 1, day, tzinfo=timezone.utc),
        clawed_back_at=datetime(2026, 1, back_day, tzinfo=timezone.utc),
        clawback_reason="reopened",
    )


def item(number, value, cls, episodes):
    return WorkItem(number, f"Item {number}", value / 1000, value, cls, episodes)


def worked_example():
    """Section 5 of the method note, split into individual issues."""
    items = [
        item(1, 20000, "A", [accepted(10)]),          # agent work that stuck
        item(2, 5000, "A", [clawed(12, 20)]),         # agent work reverted in window
        item(3, 20000, "H", [accepted(15)]),          # human work
    ]
    d = date(2026, 1, 20)
    hours = [
        HoursEntry(d, 1, "build", 20),    # human build time on agent items
        HoursEntry(d, 1, "review", 50),
        HoursEntry(d, 2, "review", 10),
        HoursEntry(d, 3, "build", 280),
    ]
    agent_costs = [
        AgentCostEntry(d, 1, "model", 3000),
        AgentCostEntry(d, 2, "compute", 700),
        AgentCostEntry(d, 2, "ci", 300),
    ]
    return compute(config(), AS_OF, items, hours, agent_costs)


def test_method_note_section_5_worked_example():
    r = worked_example()

    assert r.pv == 50000
    assert r.gross_ev == 45000
    assert r.clawback == 5000
    assert r.ev == 40000
    assert (r.ac_build, r.ac_review, r.ac_agent, r.ac) == (30000, 6000, 4000, 40000)

    assert f"{r.cpi:.2f}" == "1.00"
    assert f"{r.spi:.2f}" == "0.80"
    assert round(r.eac) == 100000
    assert f"{r.rework_rate * 100:.1f}" == "11.1"
    assert f"{r.agent_cost_share * 100:.0f}" == "10"
    assert f"{r.review_load_ratio:.1f}" == "1.5"

    a, h = r.by_class["A"], r.by_class["H"]
    assert (a.ev, a.ac) == (20000, 12000)
    assert (a.ac_agent, a.ac_review, a.ac_build) == (4000, 6000, 2000)
    assert (h.ev, h.ac) == (20000, 28000)
    assert f"{a.cpi:.2f}" == "1.67"
    assert f"{h.cpi:.2f}" == "0.71"
    assert r.by_class["M"].cpi is None


def test_method_note_section_5_classic_evm_column():
    r = worked_example()
    assert (r.classic_ev, r.classic_ac) == (45000, 30000)
    assert f"{r.classic_cpi:.2f}" == "1.50"
    assert f"{r.classic_spi:.2f}" == "0.90"
    assert round(r.classic_eac) == 66667


def test_empty_project_never_crashes():
    r = compute(config(), date(2026, 1, 1), [], [], [])
    assert r.pv == 0 and r.ev == 0 and r.ac == 0
    for value in (r.cpi, r.spi, r.eac, r.rework_rate, r.agent_cost_share,
                  r.review_load_ratio, r.classic_cpi, r.classic_eac):
        assert value is None
    for c in r.by_class.values():
        assert c.cpi is None


def test_costs_with_no_value_give_zero_cpi_and_na_eac():
    hours = [HoursEntry(date(2026, 1, 10), None, "build", 10)]
    r = compute(config(), AS_OF, [], hours, [])
    assert r.cpi == 0
    assert r.eac is None


def test_costs_after_as_of_are_ignored():
    hours = [HoursEntry(date(2026, 3, 1), None, "build", 10)]
    costs = [AgentCostEntry(date(2026, 3, 1), None, "model", 99)]
    r = compute(config(), AS_OF, [], hours, costs)
    assert r.ac == 0


def test_costs_without_item_or_unknown_item_are_unassigned():
    hours = [HoursEntry(date(2026, 1, 10), None, "review", 1),
             HoursEntry(date(2026, 1, 10), 99, "build", 2)]
    r = compute(config(), AS_OF, [], hours, [])
    assert r.by_class[UNASSIGNED].ac == 300
    assert any("#99" in w for w in r.warnings)


def test_class_totals_add_up():
    r = worked_example()
    assert sum(c.ev for c in r.by_class.values()) == pytest.approx(r.ev)
    assert sum(c.ac for c in r.by_class.values()) == pytest.approx(r.ac)


def test_items_accepted_count_excludes_fully_clawed_items():
    r = worked_example()
    assert r.by_class["A"].items_accepted == 1
    assert r.by_class["H"].items_accepted == 1
