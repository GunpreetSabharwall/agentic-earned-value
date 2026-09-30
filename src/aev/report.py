"""Write AEV-REPORT.md and the shields.io badge file."""

from __future__ import annotations

import json
from typing import Optional

from . import METHOD_NOTE_URL, __version__
from .calculator import UNASSIGNED, Results
from .items import AGENT, HUMAN, MIXED

NA = "n/a"

CLASS_LABELS = {
    AGENT: "Agent-authored (A)",
    HUMAN: "Human-authored (H)",
    MIXED: "Mixed (M)",
    UNASSIGNED: "Unassigned",
}


def money(value: Optional[float], symbol: str = "$") -> str:
    if value is None:
        return NA
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.0f}"


def ratio(value: Optional[float]) -> str:
    return NA if value is None else f"{value:.2f}"


def percent(value: Optional[float]) -> str:
    return NA if value is None else f"{value * 100:.1f}%"


def hours(value: float) -> str:
    return f"{value:,.1f}".rstrip("0").rstrip(".")


def _budget_phrase(cpi: Optional[float]) -> Optional[str]:
    if cpi is None:
        return None
    if round(cpi, 2) == 1.0:
        return "on budget"
    return "under budget" if cpi > 1 else "over budget"


def _schedule_phrase(spi: Optional[float]) -> Optional[str]:
    if spi is None:
        return None
    if round(spi, 2) == 1.0:
        return "on schedule"
    return "ahead of schedule" if spi > 1 else "behind schedule"


def what_this_means(r: Results, symbol: str = "$") -> str:
    """A short plain-English summary of the result."""
    if r.cpi is not None:
        first = f"For every {symbol}1 spent, the project has earned {symbol}{r.cpi:.2f} of value"
    else:
        first = "No cost has been recorded yet, so cost efficiency cannot be measured"

    status = [p for p in (_budget_phrase(r.cpi), _schedule_phrase(r.spi)) if p]
    if status:
        sentence = f"{first}; it is {' and '.join(status)}."
    else:
        # SPI is only n/a when nothing was planned to be done yet.
        sentence = f"{first}, and no work was planned to be done yet."

    if r.rework_rate:
        sentence += (
            f" {percent(r.rework_rate)} of the work that was marked done "
            f"did not stick and was taken back."
        )
    return sentence


def render_report(r: Results, config, repo: str = "") -> str:
    s = config.currency_symbol
    m = lambda v: money(v, s)  # noqa: E731
    lines = []
    add = lines.append

    add("# Agentic Earned Value (AEV) report")
    add("")
    where = f" for `{repo}`" if repo else ""
    add(f"As of **{r.as_of.isoformat()}**{where}. "
        f"Calculated with the [AEV method note v0.1]({METHOD_NOTE_URL}).")
    add("")
    add(f"**What this means:** {what_this_means(r, s)}")
    add("")

    add("## Summary")
    add("")
    add("| Indicator | Value | Meaning |")
    add("|---|---:|---|")
    add(f"| Budget at Completion (BAC) | {m(r.bac)} | Total planned budget |")
    add(f"| Planned Value (PV) | {m(r.pv)} | Value planned to be done by now |")
    add(f"| Earned Value (EV) | {m(r.ev)} | Value of accepted work that stuck |")
    add(f"| Actual Cost (AC) | {m(r.ac)} | People + review + agent spend so far |")
    add(f"| CPI = EV / AC | {ratio(r.cpi)} | Below 1.00 = over budget |")
    add(f"| SPI = EV / PV | {ratio(r.spi)} | Below 1.00 = behind schedule |")
    add(f"| EAC = AC + (BAC − EV) / CPI | {m(r.eac)} | Forecast total cost |")
    add("")

    add("## Classic EVM vs. AEV")
    add("")
    add("Classic EVM counts only build labor and never takes value back. "
        "AEV adds review and agent costs and claws back work that did not stick.")
    add("")
    add("| Indicator | Classic EVM (labor only, no clawback) | AEV |")
    add("|---|---:|---:|")
    add(f"| EV | {m(r.classic_ev)} | {m(r.ev)} |")
    add(f"| AC | {m(r.classic_ac)} | {m(r.ac)} |")
    add(f"| CPI | {ratio(r.classic_cpi)} | {ratio(r.cpi)} |")
    add(f"| SPI | {ratio(r.classic_spi)} | {ratio(r.spi)} |")
    add(f"| EAC | {m(r.classic_eac)} | {m(r.eac)} |")
    add("")

    add("## New AEV indicators")
    add("")
    add("| Indicator | Formula | Value | What it tells you |")
    add("|---|---|---:|---|")
    add(f"| Rework Rate | Clawback / Gross EV | {percent(r.rework_rate)} | "
        f"Share of \"done\" work that did not stick |")
    add(f"| Agent Cost Share | AC_agent / AC | {percent(r.agent_cost_share)} | "
        f"How much of spend goes to agents |")
    rl = ratio(r.review_load_ratio)
    rl_note = (f"{s}{r.review_load_ratio:.2f} of human review per {s}1 of agent spend"
               if r.review_load_ratio is not None else f"Human oversight per {s}1 of agent spend")
    add(f"| Review Load Ratio | AC_review / AC_agent | {rl} | {rl_note} |")
    add("")

    add("## By authorship class")
    add("")
    add("A = all merged PRs by agent accounts, H = none, M = mixed. "
        "Unassigned = costs with no issue number, or for issues with no merged PR yet.")
    add("")
    add("| Class | Items earning value | EV | AC | CPI |")
    add("|---|---:|---:|---:|---:|")
    total_items = 0
    for key in (AGENT, HUMAN, MIXED, UNASSIGNED):
        c = r.by_class[key]
        total_items += c.items_accepted
        add(f"| {CLASS_LABELS[key]} | {c.items_accepted} | {m(c.ev)} | {m(c.ac)} | {ratio(c.cpi)} |")
    add(f"| **Total** | **{total_items}** | **{m(r.ev)}** | **{m(r.ac)}** | **{ratio(r.cpi)}** |")
    add("")

    add("## Where the numbers come from")
    add("")
    add("| Item | Value |")
    add("|---|---:|")
    add(f"| Gross EV (all accepted items) | {m(r.gross_ev)} |")
    add(f"| Clawback (reverted or reopened within {config.stabilization_window_days} days) | {m(r.clawback)} |")
    add(f"| EV = Gross EV − Clawback | {m(r.ev)} |")
    add(f"| AC_build ({hours(r.build_hours)} h × {m(config.hourly_rate)}) | {m(r.ac_build)} |")
    add(f"| AC_review ({hours(r.review_hours)} h × {m(config.hourly_rate)}) | {m(r.ac_review)} |")
    add(f"| AC_agent | {m(r.ac_agent)} |")
    for category in sorted(r.agent_cost_by_category):
        add(f"| &nbsp;&nbsp;agent: {category} | {m(r.agent_cost_by_category[category])} |")
    add(f"| Budgeted value of all `aev-points` issues | {m(r.labelled_value)} |")
    add("")

    add("## Clawed-back items")
    add("")
    clawed = [(i, e) for i in r.items for e in i.episodes if e.clawed_back]
    if not clawed:
        add("None. No accepted item was reopened or reverted within the stabilization window.")
    else:
        add("| Issue | Title | Value | Accepted | Clawed back | Reason |")
        add("|---|---|---:|---|---|---|")
        for item, ep in clawed:
            title = item.title.replace("|", "\\|")
            add(f"| #{item.number} | {title} | {m(item.value)} | "
                f"{ep.accepted_at.date().isoformat()} | {ep.clawed_back_at.date().isoformat()} | "
                f"{ep.clawback_reason} |")
    add("")

    if r.warnings:
        add("## Data notes")
        add("")
        for warning in r.warnings:
            add(f"- {warning}")
        add("")

    add("## Assumptions")
    add("")
    add(f"- Planned value grows in a straight line from {config.start_date.isoformat()} "
        f"to {config.end_date.isoformat()}.")
    add(f"- Hourly rate: {m(config.hourly_rate)}. Stabilization window: "
        f"{config.stabilization_window_days} days.")
    accounts = ", ".join(f"`{a}`" for a in config.agent_accounts) or "none listed"
    add(f"- Agent accounts: {accounts}.")
    add("- Hours and agent costs are entered by hand in `.aev/hours.csv` and "
        "`.aev/agent-costs.csv`. Review time is self-reported.")
    add("")
    add(f"_Generated by AEV reference tool v{__version__}._")
    add("")
    return "\n".join(lines)


def badge_color(cpi: Optional[float]) -> str:
    if cpi is None:
        return "lightgrey"
    if round(cpi, 2) >= 1.0:
        return "brightgreen"
    if cpi >= 0.9:
        return "yellow"
    return "red"


def render_badge(r: Results) -> str:
    """shields.io 'endpoint' JSON: https://shields.io/badges/endpoint-badge"""
    badge = {
        "schemaVersion": 1,
        "label": "AEV CPI",
        "message": ratio(r.cpi),
        "color": badge_color(r.cpi),
    }
    return json.dumps(badge, indent=2) + "\n"
