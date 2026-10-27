"""The five-initiative demo portfolio (examples/portfolio) tells the stories the talks rely on."""

import contextlib
import io
import json
from pathlib import Path

import pytest

from aev import cli

PORTFOLIO = Path(__file__).resolve().parents[1] / "examples" / "portfolio"
SLUGS = ["agent-gateway", "cloud-modernization", "data-integration", "developer-productivity", "security-automation"]


def run(tmp_path, slug, state):
    folder = PORTFOLIO / slug
    cfg = yaml_free_config(folder, tmp_path)
    out = tmp_path / f"{slug}-{state}.json"
    with contextlib.redirect_stdout(io.StringIO()):
        assert cli.run(["--config", str(cfg), "--hours", str(folder / "hours.csv"),
                        "--agent-costs", str(folder / "agent-costs.csv"),
                        "--snapshot", str(folder / f"issues-{state}.json"), "--as-of", "2026-11-10",
                        "--repo", slug, "--output", str(tmp_path / "r.md"), "--badge", str(tmp_path / "b.json"),
                        "--json", str(out)]) == 0
    return out.read_text(encoding="utf-8")


def yaml_free_config(folder, tmp_path):
    """AEV settings from the Program Hub initiative config, the way run_aev.py builds them."""
    import yaml
    from datetime import date, timedelta
    cfg = yaml.safe_load((folder / "program-hub-config.yml").read_text())
    a = cfg["aev"]
    start = cfg["week_start"] if isinstance(cfg["week_start"], date) else date.fromisoformat(cfg["week_start"])
    settings = {k: a[k] for k in ("budget_at_completion", "value_per_point", "hourly_rate",
                                  "stabilization_window_days", "agent_accounts", "agent_label")}
    settings.update(start_date=start.isoformat(),
                    end_date=(start + timedelta(weeks=cfg["duration_weeks"])).isoformat(),
                    teams={p["name"]: p["label"] for p in cfg["pods"]})
    path = tmp_path / f"{folder.name}.yml"
    path.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
    return path


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("state", ["before", "slot1", "slot1-reverted"])
def test_committed_results_are_up_to_date(tmp_path, slug, state):
    assert run(tmp_path, slug, state) == (PORTFOLIO / slug / "results" / f"{state}.json").read_text(encoding="utf-8")


def health(slug, state="before"):
    return json.loads((PORTFOLIO / slug / "results" / f"{state}.json").read_text())["summary"]["health"]


def test_each_initiative_tells_its_story():
    assert health("agent-gateway") == "brightgreen"
    assert health("cloud-modernization") == "yellow"
    assert health("data-integration") == "red"
    assert health("developer-productivity") == "brightgreen"
    assert health("security-automation") == "brightgreen"
    di = json.loads((PORTFOLIO / "data-integration" / "results" / "before.json").read_text())
    assert di["indicators"]["rework_rate"] > 0.2 and di["classic"]["cpi"] > 1.5
    # A live demo on cloud modernization flips value health on stage.
    assert (health("cloud-modernization", "slot1"), health("cloud-modernization", "slot1-reverted")) == ("brightgreen", "yellow")


@pytest.mark.parametrize("slug", SLUGS)
def test_seed_plan_matches_the_snapshot(slug):
    plan = json.loads((PORTFOLIO / slug / "seed-plan.json").read_text())
    steps = plan["steps"]
    assert [s["number"] for s in steps] == list(range(1, len(steps) + 1))  # GitHub numbering
    assert [s["slot"] for s in plan["slots"]] == [1, 2, 3]
    snap = json.loads((PORTFOLIO / slug / "issues-before.json").read_text())["issues"]
    pr_steps = {s["number"]: s for s in steps if s["step"] == "pr"}
    for issue in snap:
        for pr in issue["linked_prs"]:
            assert pr_steps[pr["number"]]["issue"] == issue["number"]
            assert pr_steps[pr["number"]]["hold"] is False
