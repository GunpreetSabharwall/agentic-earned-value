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
from .items import AGENT, CLASSES, MIXED, WorkItem

UNASSIGNED = "Unassigned"
NO_TEAM = "No team"


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
class TeamResult:
    """One team's results, split by authorship class (A, H, M, Unassigned)."""

    name: str
    label: Optional[str]
    by_class: Dict[str, ClassResult] = field(default_factory=dict)

    @property
    def ev(self) -> float:
        return sum(c.ev for c in self.by_class.values())

    @property
    def ac(self) -> float:
        return sum(c.ac for c in self.by_class.values())

    @property
    def cpi(self) -> Optional[float]:
        return f.cpi(self.ev, self.ac)

    @property
    def items_accepted(self) -> int:
        return sum(c.items_accepted for c in self.by_class.values())


@dataclass
class Activity:
    """What AI-activity dashboards usually show. Counts, not value."""

    merged_prs: int = 0
    agent_prs: int = 0
    mixed_prs: int = 0
    human_prs: int = 0
    items_closed: int = 0  # accepted at least once, whether or not it stuck
    agent_spend: float = 0.0
    tokens: float = 0.0

    @property
    def agent_pr_share(self) -> Optional[float]:
        return f.safe_div(self.agent_prs, self.merged_prs)

    @property
    def ai_assisted_pr_share(self) -> Optional[float]:
        return f.safe_div(self.agent_prs + self.mixed_prs, self.merged_prs)


def team_of(item: WorkItem, teams: Dict[str, str]) -> str:
    """The first team (in config order) whose label the item carries."""
    labels = {label.strip().lower() for label in item.labels}
    for name, label in teams.items():
        if label.strip().lower() in labels:
            return name
    return NO_TEAM


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
    by_team: Dict[str, TeamResult] = field(default_factory=dict)
    activity: Activity = field(default_factory=Activity)
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
    # Each value or cost lands in one class bucket overall and, when teams are
    # configured, in the same class bucket of its team.
    class_names = CLASSES + (UNASSIGNED,)
    by_class = {name: ClassResult(name) for name in class_names}
    class_of = {i.number: i.authorship for i in items}

    by_team: Dict[str, TeamResult] = {}
    team_names = list(config.teams) + [NO_TEAM]
    if config.teams:
        for name in team_names:
            by_team[name] = TeamResult(name, config.teams.get(name),
                                       {c: ClassResult(c) for c in class_names})
    team_by_item = {i.number: team_of(i, config.teams) for i in items}

    def buckets(item_number: Optional[int]) -> List[ClassResult]:
        cls = class_of.get(item_number) if item_number is not None else None
        key = cls if cls in CLASSES else UNASSIGNED
        found = [by_class[key]]
        if by_team:
            found.append(by_team[team_by_item.get(item_number, NO_TEAM)].by_class[key])
        return found

    for item in items:
        if item.episodes:
            for target in buckets(item.number):
                target.ev += item.ev
                if item.ev > 0:
                    target.items_accepted += 1
    for h in hours:
        for target in buckets(h.item):
            if h.type == "build":
                target.ac_build += f.labor_cost(h.hours, rate)
            else:
                target.ac_review += f.labor_cost(h.hours, rate)
    for c in agent_costs:
        for target in buckets(c.item):
            target.ac_agent += c.amount

    # Drop the "No team" row when nothing landed in it.
    if by_team and not any(c.ev or c.ac for c in by_team[NO_TEAM].by_class.values()):
        del by_team[NO_TEAM]

    # --- Activity: what AI dashboards usually count -------------------------
    activity = Activity(agent_spend=ac_agent, tokens=sum(c.tokens for c in agent_costs))
    seen_prs = {}
    for item in items:
        if item.episodes:
            activity.items_closed += 1
        for pr in item.merged_prs:
            seen_prs.setdefault(pr.get("number") or id(pr), pr["class"])
    activity.merged_prs = len(seen_prs)
    activity.agent_prs = sum(1 for c in seen_prs.values() if c == AGENT)
    activity.mixed_prs = sum(1 for c in seen_prs.values() if c == MIXED)
    activity.human_prs = activity.merged_prs - activity.agent_prs - activity.mixed_prs

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
        by_team=by_team,
        activity=activity,
        items=items,
        warnings=warnings,
    )
