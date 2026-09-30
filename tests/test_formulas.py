"""One test (or more) for every formula in the method note."""

from datetime import date

import pytest

from aev import formulas as f


# --- safe division ------------------------------------------------------------

def test_safe_div_normal():
    assert f.safe_div(1, 4) == 0.25


def test_safe_div_is_true_division_for_integers():
    assert f.safe_div(2, 3) == pytest.approx(0.6667, abs=1e-4)


@pytest.mark.parametrize("num,den", [(1, 0), (0, 0), (None, 5), (5, None)])
def test_safe_div_returns_none_instead_of_crashing(num, den):
    assert f.safe_div(num, den) is None


# --- planned value (linear) ------------------------------------------------------

START, END = date(2026, 1, 1), date(2026, 1, 11)  # 10 days


def test_pv_before_start_is_zero():
    assert f.planned_value(1000, START, END, date(2025, 12, 1)) == 0


def test_pv_on_start_is_zero():
    assert f.planned_value(1000, START, END, START) == 0


def test_pv_midway_is_linear():
    assert f.planned_value(1000, START, END, date(2026, 1, 4)) == pytest.approx(300)


def test_pv_after_end_is_bac():
    assert f.planned_value(1000, START, END, date(2027, 1, 1)) == 1000


# --- actual cost ------------------------------------------------------------------

def test_labor_cost():
    assert f.labor_cost(300, 100) == 30000


def test_actual_cost_is_sum_of_three_parts():
    assert f.actual_cost(30000, 6000, 4000) == 40000


# --- earned value -----------------------------------------------------------------

def test_earned_value_subtracts_clawback():
    assert f.earned_value(45000, 5000) == 40000


# --- core indicators -------------------------------------------------------------

def test_cpi():
    assert f.cpi(40000, 32000) == 1.25


def test_cpi_zero_cost_is_na():
    assert f.cpi(40000, 0) is None


def test_spi():
    assert f.spi(40000, 50000) == 0.8


def test_spi_zero_pv_is_na():
    assert f.spi(100, 0) is None


def test_eac():
    # AC + (BAC - EV) / CPI = 20000 + (100000 - 25000) / 1.25
    assert f.eac(20000, 100000, 25000, 1.25) == 80000


def test_eac_na_when_cpi_na_or_zero():
    assert f.eac(20000, 100000, 0, None) is None
    assert f.eac(20000, 100000, 0, 0.0) is None


# --- new AEV indicators ----------------------------------------------------------

def test_rework_rate():
    assert f.rework_rate(5000, 50000) == 0.1


def test_rework_rate_na_without_gross_ev():
    assert f.rework_rate(0, 0) is None


def test_agent_cost_share():
    assert f.agent_cost_share(1000, 4000) == 0.25


def test_agent_cost_share_na_without_cost():
    assert f.agent_cost_share(0, 0) is None


def test_review_load_ratio():
    assert f.review_load_ratio(3000, 2000) == 1.5


def test_review_load_ratio_na_without_agent_cost():
    assert f.review_load_ratio(3000, 0) is None


# --- Section 5 worked example, using only the formulas ------------------------------

def test_method_note_section_5_formulas():
    bac = 100000
    pv = f.planned_value(bac, date(2026, 1, 5), date(2026, 3, 16), date(2026, 2, 9))
    assert pv == 50000

    ev = f.earned_value(45000, 5000)
    ac_build = f.labor_cost(300, 100)
    ac_review = f.labor_cost(60, 100)
    ac_agent = 4000
    ac = f.actual_cost(ac_build, ac_review, ac_agent)
    assert (ev, ac) == (40000, 40000)

    cpi = f.cpi(ev, ac)
    assert round(cpi, 2) == 1.00
    assert round(f.spi(ev, pv), 2) == 0.80
    assert round(f.eac(ac, bac, ev, cpi)) == 100000
    assert round(f.rework_rate(5000, 45000) * 100, 1) == 11.1
    assert round(f.agent_cost_share(ac_agent, ac) * 100, 1) == 10.0
    assert round(f.review_load_ratio(ac_review, ac_agent), 2) == 1.50
    assert round(f.cpi(20000, 12000), 2) == 1.67  # CPI_A
    assert round(f.cpi(20000, 28000), 2) == 0.71  # CPI_H

    # Classic EVM column: labor only, no clawback.
    classic_cpi = f.cpi(45000, 30000)
    assert round(classic_cpi, 2) == 1.50
    assert round(f.spi(45000, pv), 2) == 0.90
    assert round(f.eac(30000, bac, 45000, classic_cpi)) == 66667
