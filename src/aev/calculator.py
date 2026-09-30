"""Combine work items and costs into the full set of AEV results.

No GitHub calls and no file reading here: give it data, get numbers back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from . import formulas as f
from .config import Config
from .costs import AgentCostEntry, HoursEntry
from .items import CLASSES, WorkItem

UNASSIGNED = "Unassigned"


@dataclass
class ClassResult:
    name: str
    items_accepted: int = 0
    ev: float = 0.0
    ac_build: float = 0.0
    ac_review: float = 0.0
    ac_agent: float = 0.0

    @property
    def ac(self) -> float:
        return f.actual_cost(self.ac_build, self.ac_review, self.ac_agent)

    @property
    def cpi(self) -> Optional[float]:
        return f.cpi(self.ev, self.ac)


@dataclass
class Results:
    as_of: date
    bac: float
    pv: float
    gross_ev: float
    clawback: float
    ev: float
    build_hours: float
    review_hours: float
    ac_build: float
    ac_review: float
    ac_agent: float
    ac: float
    cpi: Optional[float]
    spi: Optional[float]
    eac: Optional[float]
    rework_rate: Optional[float]
    agent_cost_share: Optional[float]
    review_load_ratio: Optional[float]
    classic_ev: float
    classic_ac: float
    classic_cpi: Optional[float]
    classic_spi: Optional[float]
    classic_eac: Optional[float]
    by_class: Dict[str, ClassResult]
    agent_cost_by_category: Dict[str, float]
    labelled_value: float
    items: List[WorkItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def compute(
    config: Config,
    as_of: date,
    items: List[WorkItem],
    hours: List[HoursEntry],
    agent_costs: List[AgentCostEntry],
    warnings: Optional[List[str]] = None,
) -> Results:
    warnings = list(warnings or [])
    rate = config.hourly_rate

    # Only count costs recorded on or before the "as of" date.
    hours = [h for h in hours if h.day <= as_of]
    agent_costs = [c for c in agent_costs if c.day <= as_of]

    # --- Value ---------------------------------------------------------------
    gross_ev = sum(i.gross_ev for i in items)
    clawback = sum(i.clawback for i in items)
    ev = f.earned_value(gross_ev, clawback)
    pv = f.planned_value(config.budget_at_completion, config.start_date, config.end_date, as_of)

    # --- Cost ----------------------------------------------------------------
    build_hours = sum(h.hours for h in hours if h.type == "build")
    review_hours = sum(h.hours for h in hours if h.type == "review")
    ac_build = f.labor_cost(build_hours, rate)
    ac_review = f.labor_cost(review_hours, rate)
    ac_agent = sum(c.amount for c in agent_costs)
    ac = f.actual_cost(ac_build, ac_review, ac_agent)

    by_category: Dict[str, float] = {}
    for c in agent_costs:
        by_category[c.category] = by_category.get(c.category, 0.0) + c.amount

    # --- Core and new indicators --------------------------------------------
    cpi = f.cpi(ev, ac)
    bac = config.budget_at_completion

    # --- Classic EVM, for comparison: labor only (AC_build), no clawback. ----
    classic_ev = gross_ev
    classic_ac = ac_build
    classic_cpi = f.cpi(classic_ev, classic_ac)

    # --- Attribution by authorship class ------------------------------------
    by_class = {name: ClassResult(name) for name in CLASSES + (UNASSIGNED,)}
    class_of = {i.number: i.authorship for i in items}

    def bucket(item_number: Optional[int]) -> ClassResult:
        cls = class_of.get(item_number) if item_number is not None else None
        return by_class[cls] if cls in CLASSES else by_class[UNASSIGNED]

    for item in items:
        if item.episodes:
            target = bucket(item.number)
            target.ev += item.ev
            if item.ev > 0:
                target.items_accepted += 1
    for h in hours:
        target = bucket(h.item)
        if h.type == "build":
            target.ac_build += f.labor_cost(h.hours, rate)
        else:
            target.ac_review += f.labor_cost(h.hours, rate)
    for c in agent_costs:
        bucket(c.item).ac_agent += c.amount

    known = set(class_of)
    for number in sorted({e.item for e in list(hours) + list(agent_costs) if e.item is not None} - known):
        warnings.append(f"Cost rows mention issue #{number}, which was not found; counted as Unassigned.")

    return Results(
        as_of=as_of,
        bac=bac,
        pv=pv,
        gross_ev=gross_ev,
        clawback=clawback,
        ev=ev,
        build_hours=build_hours,
        review_hours=review_hours,
        ac_build=ac_build,
        ac_review=ac_review,
        ac_agent=ac_agent,
        ac=ac,
        cpi=cpi,
        spi=f.spi(ev, pv),
        eac=f.eac(ac, bac, ev, cpi),
        rework_rate=f.rework_rate(clawback, gross_ev),
        agent_cost_share=f.agent_cost_share(ac_agent, ac),
        review_load_ratio=f.review_load_ratio(ac_review, ac_agent),
        classic_ev=classic_ev,
        classic_ac=classic_ac,
        classic_cpi=classic_cpi,
        classic_spi=f.spi(classic_ev, pv),
        classic_eac=f.eac(classic_ac, bac, classic_ev, classic_cpi),
        by_class=by_class,
        agent_cost_by_category=by_category,
        labelled_value=sum(i.value for i in items),
        items=items,
        warnings=warnings,
    )
