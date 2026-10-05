"""Command line entry point: ``python -m aev``.

Examples::

    python -m aev --demo                      # sample data, no GitHub needed
    python -m aev --repo owner/name           # real run (needs GITHUB_TOKEN)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from .calculator import compute
from .config import ConfigError, load_config
from .costs import load_agent_costs, load_hours
from .items import build_work_items, end_of_day
from .report import render_badge, render_report

DEMO_DIR = Path(__file__).resolve().parents[2] / "examples" / "demo"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aev", description="Compute Agentic Earned Value (AEV).")
    p.add_argument("--demo", action="store_true",
                   help="Run on the sample data in examples/demo (no GitHub access).")
    p.add_argument("--config", default=".aev/config.yml",
                   help="Config file. hours.csv and agent-costs.csv are read from the same folder.")
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""),
                   help="GitHub repository as owner/name (default: $GITHUB_REPOSITORY).")
    p.add_argument("--snapshot", help="Read issue data from this JSON file instead of GitHub.")
    p.add_argument("--save-snapshot", help="Also save the issue data fetched from GitHub to this file.")
    p.add_argument("--output", help="Where to write the report (default: AEV-REPORT.md).")
    p.add_argument("--badge", help="Where to write the badge JSON (default: .aev/badge.json).")
    p.add_argument("--as-of", help="Calculate as of this date (YYYY-MM-DD). Default: config or today.")
    return p


def run(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.demo:
        args.config = str(DEMO_DIR / ".aev" / "config.yml")
        args.snapshot = str(DEMO_DIR / "issues.json")
        args.output = args.output or str(DEMO_DIR / "AEV-REPORT.md")
        args.badge = args.badge or str(DEMO_DIR / ".aev" / "badge.json")
        args.repo = "example/demo-project"
    args.output = args.output or "AEV-REPORT.md"
    args.badge = args.badge or ".aev/badge.json"

    try:
        config = load_config(Path(args.config))
    except ConfigError as exc:
        print(f"Config problem: {exc}", file=sys.stderr)
        return 2

    if args.as_of:
        as_of = date.fromisoformat(args.as_of)
    elif config.as_of_date:
        as_of = config.as_of_date
    else:
        as_of = datetime.now(timezone.utc).date()

    # --- Issue data: from a file or from GitHub -----------------------------
    if args.snapshot:
        with open(args.snapshot, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    else:
        from .github_data import GitHubError, fetch_snapshot

        since = datetime.combine(config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        since -= timedelta(days=config.stabilization_window_days)
        try:
            snapshot = fetch_snapshot(args.repo, os.environ.get("GITHUB_TOKEN", ""), since)
        except GitHubError as exc:
            print(f"Could not read data from GitHub: {exc}", file=sys.stderr)
            return 3
        if args.save_snapshot:
            Path(args.save_snapshot).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    # --- Costs ----------------------------------------------------------------
    folder = Path(args.config).parent
    hours, hour_warnings = load_hours(folder / "hours.csv")
    agent_costs, cost_warnings = load_agent_costs(folder / "agent-costs.csv")

    # --- Calculate ------------------------------------------------------------
    items, item_warnings = build_work_items(
        snapshot.get("issues", []),
        config.value_per_point,
        config.agent_accounts,
        config.stabilization_window_days,
        end_of_day(as_of),
        agent_label=config.agent_label,
    )
    results = compute(
        config, as_of, items, hours, agent_costs,
        warnings=hour_warnings + cost_warnings + item_warnings,
    )

    # --- Write outputs --------------------------------------------------------
    report = render_report(results, config, repo=args.repo or snapshot.get("repo", ""))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report, encoding="utf-8")
    Path(args.badge).parent.mkdir(parents=True, exist_ok=True)
    Path(args.badge).write_text(render_badge(results), encoding="utf-8")

    print(report)
    print(f"Report written to {args.output}")
    print(f"Badge written to {args.badge}")
    return 0


def main() -> None:
    sys.exit(run())
