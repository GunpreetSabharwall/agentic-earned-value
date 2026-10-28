"""Write all AEV results as JSON (``.aev/aev.json``).

This is the machine-readable twin of AEV-REPORT.md. Other tools (for example
Program Hub, or a dashboard) read this file instead of parsing the report.
The layout is versioned with ``schema``; fields are only ever added.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from . import __version__
from .calculator import ClassResult, Results, team_of
from .report import badge_color, what_this_means

SCHEMA = "aev-results/1"


def _money(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(float(value), 2)


def _ratio(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(float(value), 4)


def _time(value: Optional[datetime]) -> Optional[str]:
    return None if value is None else value.isoformat().replace("+00:00", "Z")


def _class(c: ClassResult) -> dict:
    return {
        "items_accepted": c.items_accepted,
        "ev": _money(c.ev),
        "ac": _money(c.ac),
        "ac_build": _money(c.ac_build),
        "ac_review": _money(c.ac_review),
        "ac_agent": _money(c.ac_agent),
        "cpi": _ratio(c.cpi),
    }


def results_to_dict(r: Results, config, repo: str = "") -> dict:
    a = r.activity
    return {
        "schema": SCHEMA,
        "tool_version": __version__,
        "method_note": "0.1",
        "repo": repo,
        "as_of": r.as_of.isoformat(),
        "config": {
            "budget_at_completion": _money(config.budget_at_completion),
            "value_per_point": _money(config.value_per_point),
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "hourly_rate": _money(config.hourly_rate),
            "stabilization_window_days": config.stabilization_window_days,
            "agent_accounts": list(config.agent_accounts),
            "agent_label": config.agent_label,
            "currency_symbol": config.currency_symbol,
            "teams": dict(config.teams),
        },
        "summary": {
            "bac": _money(r.bac),
            "pv": _money(r.pv),
            "ev": _money(r.ev),
            "ac": _money(r.ac),
            "cpi": _ratio(r.cpi),
            "spi": _ratio(r.spi),
            "eac": _money(r.eac),
            "health": badge_color(r.cpi),
            "what_this_means": what_this_means(r, config.currency_symbol),
        },
        "classic": {
            "ev": _money(r.classic_ev),
            "ac": _money(r.classic_ac),
            "cpi": _ratio(r.classic_cpi),
            "spi": _ratio(r.classic_spi),
            "eac": _money(r.classic_eac),
        },
        "indicators": {
            "rework_rate": _ratio(r.rework_rate),
            "agent_cost_share": _ratio(r.agent_cost_share),
            "review_load_ratio": _ratio(r.review_load_ratio),
        },
        "value": {
            "gross_ev": _money(r.gross_ev),
            "clawback": _money(r.clawback),
            "ev": _money(r.ev),
            "labelled_value": _money(r.labelled_value),
        },
        "cost": {
            "build_hours": round(r.build_hours, 2),
            "review_hours": round(r.review_hours, 2),
            "ac_build": _money(r.ac_build),
            "ac_review": _money(r.ac_review),
            "ac_agent": _money(r.ac_agent),
            "agent_by_category": {k: _money(v) for k, v in sorted(r.agent_cost_by_category.items())},
        },
        "by_class": {name: _class(c) for name, c in r.by_class.items()},
        "by_team": [
            {
                "name": t.name,
                "label": t.label,
                "items_accepted": t.items_accepted,
                "ev": _money(t.ev),
                "ac": _money(t.ac),
                "cpi": _ratio(t.cpi),
                "by_class": {name: _class(c) for name, c in t.by_class.items()},
            }
            for t in r.by_team.values()
        ],
        "activity": {
            "merged_prs": a.merged_prs,
            "agent_prs": a.agent_prs,
            "mixed_prs": a.mixed_prs,
            "human_prs": a.human_prs,
            "agent_pr_share": _ratio(a.agent_pr_share),
            "ai_assisted_pr_share": _ratio(a.ai_assisted_pr_share),
            "items_closed": a.items_closed,
            "items_that_stuck": sum(1 for i in r.items if i.ev > 0),
            "agent_spend": _money(a.agent_spend),
            "tokens": int(a.tokens),
        },
        "items": [
            {
                "number": i.number,
                "title": i.title,
                "points": i.points,
                "value": _money(i.value),
                "authorship": i.authorship,
                "team": team_of(i, config.teams) if config.teams else None,
                "labels": list(i.labels),
                "gross_ev": _money(i.gross_ev),
                "clawback": _money(i.clawback),
                "ev": _money(i.ev),
                "episodes": [
                    {
                        "accepted_at": _time(e.accepted_at),
                        "clawed_back_at": _time(e.clawed_back_at),
                        "reason": e.clawback_reason,
                    }
                    for e in i.episodes
                ],
                "merged_prs": [
                    {"number": p.get("number"), "class": p["class"], "merged_at": _time(p["merged_at"])}
                    for p in i.merged_prs
                ],
            }
            for i in r.items
        ],
        "warnings": list(r.warnings),
    }


def render_json(r: Results, config, repo: str = "") -> str:
    return json.dumps(results_to_dict(r, config, repo), indent=2, ensure_ascii=False) + "\n"
