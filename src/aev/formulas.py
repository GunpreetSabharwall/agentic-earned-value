"""The AEV formulas, one small function each.

Every function here is pure: numbers in, numbers out. Nothing here talks to
GitHub or reads files. Section numbers refer to AEV-method-note-v0.1.md.

Any ratio whose bottom number is zero (or missing) returns ``None``. The
report shows ``None`` as "n/a". Nothing here ever raises ZeroDivisionError,
and all division is true (floating point) division.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

Number = Optional[float]


def safe_div(numerator: Number, denominator: Number) -> Number:
    """Return numerator / denominator, or None if that cannot be computed."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


# --- Section 4.1: planned value ------------------------------------------------

def planned_value(bac: float, start: date, end: date, as_of: date) -> float:
    """PV grows in a straight line from 0 on ``start`` to BAC on ``end``.

    Before the start date PV is 0; on or after the end date PV is BAC.
    """
    if as_of <= start:
        return 0.0
    if as_of >= end:
        return float(bac)
    total_days = (end - start).days
    elapsed_days = (as_of - start).days
    return float(bac) * elapsed_days / total_days


# --- Section 4.2: blended actual cost -----------------------------------------

def labor_cost(hours: float, hourly_rate: float) -> float:
    """Hours multiplied by the hourly rate (used for AC_build and AC_review)."""
    return float(hours) * float(hourly_rate)


def actual_cost(ac_build: float, ac_review: float, ac_agent: float) -> float:
    """AC = AC_build + AC_review + AC_agent."""
    return float(ac_build) + float(ac_review) + float(ac_agent)


# --- Section 4.3: rework-adjusted earned value --------------------------------

def earned_value(gross_ev: float, clawback: float) -> float:
    """EV (AEV) = Gross EV - Clawback."""
    return float(gross_ev) - float(clawback)


# --- Section 4.4: core indicators ----------------------------------------------

def cpi(ev: Number, ac: Number) -> Number:
    """Cost Performance Index: CPI = EV / AC."""
    return safe_div(ev, ac)


def spi(ev: Number, pv: Number) -> Number:
    """Schedule Performance Index: SPI = EV / PV."""
    return safe_div(ev, pv)


def eac(ac: Number, bac: Number, ev: Number, cpi_value: Number) -> Number:
    """Estimate at Completion: EAC = AC + (BAC - EV) / CPI."""
    if ac is None or bac is None or ev is None:
        return None
    remaining = safe_div(float(bac) - float(ev), cpi_value)
    if remaining is None:
        return None
    return float(ac) + remaining


# --- Section 4.5: new AEV indicators --------------------------------------------

def rework_rate(clawback: Number, gross_ev: Number) -> Number:
    """Rework Rate = Clawback / Gross EV."""
    return safe_div(clawback, gross_ev)


def agent_cost_share(ac_agent: Number, ac: Number) -> Number:
    """Agent Cost Share = AC_agent / AC."""
    return safe_div(ac_agent, ac)


def review_load_ratio(ac_review: Number, ac_agent: Number) -> Number:
    """Review Load Ratio = AC_review / AC_agent."""
    return safe_div(ac_review, ac_agent)
