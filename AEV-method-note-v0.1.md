# Agentic Earned Value (AEV)
## Extending Earned Value Management to Human–Agent Software Delivery

**Author:** Gunpreet Sabharwall · ORCID [0009-0000-5434-7382](https://orcid.org/0009-0000-5434-7382)
**Version:** 0.1 (draft, not yet published)
**Date:** 09-30-2026
**License:** CC BY 4.0
**Cite as:** Sabharwall, G. (2026). *Agentic Earned Value (AEV): Extending Earned Value Management to Human–Agent Software Delivery* (v0.1). Zenodo. DOI: [to be assigned]

---

## 1. Summary

Earned Value Management (EVM) is the standard way to tell whether a project is on budget and on schedule. It assumes that people do the work and that labor is the main cost.

That assumption no longer holds. In many software programs, AI agents now write code, open pull requests and fix defects. This work has new costs: model usage, compute, CI runs, and the human time spent reviewing and correcting agent output. It also has a new risk: work that looks done but gets reverted.

Classic EVM, applied without change, hides these costs and overstates progress.

**Agentic Earned Value (AEV)** is a method that keeps EVM's familiar indicators (CPI, SPI, EAC) and makes three changes:

1. **Blended Actual Cost:** agent costs and human review costs are counted in Actual Cost.
2. **Rework-adjusted Earned Value:** value is earned only when work is accepted, and taken back if it is reverted within a stabilization window.
3. **Attribution:** cost and value are split by who did the work (human, agent, or mixed), so leaders can compare efficiency.

AEV also defines three new indicators: **Rework Rate**, **Agent Cost Share**, and **Review Load Ratio**.

---

## 2. Background: classic EVM in one table

| Term | Meaning |
|---|---|
| BAC | Budget at Completion: total planned value of the work |
| PV | Planned Value: value of work scheduled to be done by now |
| EV | Earned Value: value of work actually completed by now |
| AC | Actual Cost: what has been spent by now |
| CPI = EV / AC | Cost efficiency (below 1.0 = over budget) |
| SPI = EV / PV | Schedule efficiency (below 1.0 = behind schedule) |
| EAC = AC + (BAC − EV) / CPI | Forecast total cost at current efficiency |

---

## 3. What changes when agents do the work

| Issue | Effect on classic EVM |
|---|---|
| Agent costs (model usage, compute, CI) sit outside labor budgets | AC is understated, so CPI looks better than it is |
| Human review of agent output is often not tracked separately | Oversight cost is hidden inside general effort |
| Agent work can be merged, then reverted | EV is counted early and never taken back |
| Human and agent work are mixed together | Leaders cannot see which kind of work is efficient |

---

## 4. The AEV method

### 4.1 Work items and planned value

Each work item *i* (for example, a GitHub issue) carries a **budgeted value** *BVᵢ*, in money or points. BAC is the sum of all *BVᵢ*. PV follows the plan's schedule, as in classic EVM.

Each item is also tagged with an **authorship class**:

- **H** — human-authored
- **A** — agent-authored (a person may still review it)
- **M** — mixed

### 4.2 Blended Actual Cost

```
AC = AC_build + AC_review + AC_agent
```

| Component | Includes |
|---|---|
| AC_build | Human time spent building (hours × rate) |
| AC_review | Human time spent reviewing or correcting agent output (hours × rate) |
| AC_agent | Model usage, compute, CI minutes and tool fees consumed by agents |

### 4.3 Rework-adjusted Earned Value

AEV uses a strict **accept-then-hold** earning rule:

- An item earns its value only when it is **accepted**: merged, linked issue closed, and required checks passed.
- If the item is **reverted or reopened** within a **stabilization window W** (default: 14 days), its value is **clawed back**.

```
Gross EV   = sum of BVᵢ for accepted items
Clawback   = sum of BVᵢ for items reverted or reopened within W
EV (AEV)   = Gross EV − Clawback
```

### 4.4 Core indicators

CPI, SPI and EAC keep their classic formulas, using the blended AC and rework-adjusted EV above.

```
CPI = EV / AC
SPI = EV / PV
EAC = AC + (BAC − EV) / CPI
```

### 4.5 New AEV indicators

| Indicator | Formula | What it tells you |
|---|---|---|
| Rework Rate | Clawback / Gross EV | Share of "done" work that did not stick |
| Agent Cost Share | AC_agent / AC | How much of spend goes to agents |
| Review Load Ratio | AC_review / AC_agent | Human oversight spent per $1 of agent spend |

### 4.6 Attribution by authorship class

Each class gets its own EV and AC, and so its own CPI:

```
CPI_A = EV_A / AC_A     (agent-authored work)
CPI_H = EV_H / AC_H     (human-authored work)
CPI_M = EV_M / AC_M     (mixed work)
```

AC_A includes agent costs, the review cost of agent output, and any human build time spent on agent-authored items.

---

## 5. Worked example (illustrative numbers)

A program has BAC = $100,000 over 10 weeks. At the end of week 5:

**Plan:** PV = $50,000

**Value:**
- Accepted items: Gross EV = $45,000
- Agent-authored items worth $5,000 were reverted within 14 days: Clawback = $5,000
- EV (AEV) = $45,000 − $5,000 = **$40,000**

**Cost:**
- AC_build = 300 hours × $100 = $30,000
- AC_review = 60 hours × $100 = $6,000
- AC_agent = $4,000
- AC = **$40,000**

### 5.1 Classic EVM vs. AEV

| Indicator | Classic EVM (labor only, no clawback) | AEV |
|---|---|---|
| EV | $45,000 | $40,000 |
| AC | $30,000 | $40,000 |
| CPI | **1.50** (looks under budget) | **1.00** (on budget) |
| SPI | 0.90 | **0.80** (behind schedule) |
| EAC | $66,667 | **$100,000** |

Classic EVM would report the program as comfortably under budget. AEV shows it is on budget at best and meaningfully behind schedule.

### 5.2 New indicators

| Indicator | Value |
|---|---|
| Rework Rate | $5,000 / $45,000 = **11.1%** |
| Agent Cost Share | $4,000 / $40,000 = **10%** |
| Review Load Ratio | $6,000 / $4,000 = **1.5** ($1.50 of human review per $1 of agent spend) |

### 5.3 Attribution

| Class | EV | AC | CPI |
|---|---|---|---|
| Agent-authored (A) | $20,000 | $12,000 (agent $4,000 + review $6,000 + build $2,000) | **1.67** |
| Human-authored (H) | $20,000 | $28,000 | **0.71** |
| **Total** | **$40,000** | **$40,000** | **1.00** |

In this example, agent-authored work is more cost-efficient even after rework and review, while human-authored work is running over budget. That is a decision a program leader can act on.

---

## 6. Getting the data from GitHub

| AEV input | Source |
|---|---|
| BVᵢ and schedule | Issue fields or labels (for example, points × rate), project board dates |
| Accepted | PR merged + linked issue closed + required checks passed |
| Clawback | Revert commit or issue reopened within W days |
| Authorship class | PR author (agent/bot account) or commit trailers |
| AC_agent | Agent or model provider billing export, CI minutes |
| AC_build, AC_review | Time tracking, or estimates from review activity (see limitations) |

A reference implementation (GitHub Action) is planned at: [repo URL].

---

## 7. Limitations

- **Review time is hard to measure.** Without time tracking, AC_review must be estimated from review activity. The estimate method should be stated in any report.
- **The 14-day window is a starting default.** It should be tuned per program.
- **Budgeted values depend on the planning method.** AEV inherits EVM's dependence on a sound baseline.
- **Authorship is not always clean.** The mixed class (M) exists for this, but attribution rules should be stated.
- **The example is illustrative.** Pilot results will follow in a later version.

---

## 8. Related work

- Earned Value Management for software projects: Project Management Institute learning library. [Full references to be added after formal literature search.]
- Cost taxonomies for agentic software delivery, for example: *Beyond Code Generation: Reliability, Verification, and Cost Economics in the Agentic Software Development Lifecycle*, arXiv:2609.04681.
- Agentic software project management: *Toward Agentic Software Project Management: A Vision and Roadmap*, arXiv:2601.16392.
- Earned value computed from GitHub activity for human contributors: Zerocracy (github.com/zerocracy).

AEV differs from these by combining agent cost, review cost, rework clawback and authorship attribution into EVM's cost and schedule indicators.

---

## 9. Version history

| Version | Date | Change |
|---|---|---|
| 0.1 | 09-30-2026 | First public definition of AEV |
