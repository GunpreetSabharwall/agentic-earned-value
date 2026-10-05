"""Config and CSV reading."""

from datetime import date

import pytest

from aev.config import ConfigError, load_config, parse_config
from aev.costs import load_agent_costs, load_hours, parse_item

BASE = {
    "budget_at_completion": 1000,
    "value_per_point": 10,
    "start_date": "2026-01-01",
    "end_date": "2026-02-01",
    "hourly_rate": 50,
}


def test_config_defaults():
    c = parse_config(dict(BASE))
    assert c.stabilization_window_days == 14
    assert c.agent_accounts == []
    assert c.start_date == date(2026, 1, 1)
    assert c.as_of_date is None


def test_config_accepts_money_written_with_commas():
    c = parse_config(dict(BASE, budget_at_completion="$100,000"))
    assert c.budget_at_completion == 100000


@pytest.mark.parametrize("key", ["budget_at_completion", "value_per_point", "start_date", "hourly_rate"])
def test_config_missing_value_is_clear_error(key):
    raw = dict(BASE)
    del raw[key]
    with pytest.raises(ConfigError, match=key):
        parse_config(raw)


def test_config_end_before_start_is_error():
    with pytest.raises(ConfigError, match="end_date"):
        parse_config(dict(BASE, end_date="2025-01-01"))


def test_config_bad_number_is_error():
    with pytest.raises(ConfigError, match="number"):
        parse_config(dict(BASE, hourly_rate="lots"))


def test_config_single_agent_account_as_text():
    assert parse_config(dict(BASE, agent_accounts="bot")).agent_accounts == ["bot"]


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yml")


def test_parse_item():
    assert parse_item("12") == 12
    assert parse_item("#12") == 12
    assert parse_item("") is None
    assert parse_item("  ") is None


def test_load_hours(tmp_path):
    path = tmp_path / "hours.csv"
    path.write_text(
        "Date, Item, Type, Hours\n"
        "2026-01-02,#3,build,4.5\n"
        "2026-01-02,,Review,2\n"
        "\n"
        "2026-01-02,3,coffee,1\n"
        "not-a-date,3,build,1\n",
        encoding="utf-8",
    )
    entries, warnings = load_hours(path)
    assert [(e.item, e.type, e.hours) for e in entries] == [(3, "build", 4.5), (None, "review", 2.0)]
    assert len(warnings) == 2


def test_load_agent_costs(tmp_path):
    path = tmp_path / "agent-costs.csv"
    path.write_text(
        "date,item,category,amount\n"
        "2026-01-02,3,model,\"1,200.50\"\n"
        "2026-01-02,,other,10\n"
        "2026-01-02,,ci,-5\n",
        encoding="utf-8",
    )
    entries, warnings = load_agent_costs(path)
    assert [e.amount for e in entries] == [1200.5, 10.0]
    assert len(warnings) == 2  # unknown category (kept) + negative amount (skipped)


def test_missing_cost_files_are_treated_as_empty(tmp_path):
    entries, warnings = load_hours(tmp_path / "hours.csv")
    assert entries == [] and len(warnings) == 1


def test_config_agent_label_default_and_custom():
    assert parse_config(dict(BASE)).agent_label == "aev-agent"
    assert parse_config(dict(BASE, agent_label="ai-made")).agent_label == "ai-made"
    assert parse_config(dict(BASE, agent_label=None)).agent_label == "aev-agent"
