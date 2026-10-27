# Demo use case: "The AI dashboard says green. Is it?"

Talk: **Beyond AI Productivity: Rethinking Program Governance with Agentic Earned Value**
**AI Week Great Lakes, 10 Nov 2026** (30-minute slot: about 18 minutes of slides, 12 minutes of live demo). Reusable for **AI Infrastructure Exchange 2027**.

Brings together two separate products that talk to each other in the demo:
**Program Hub AI** (governance layer: visibility, status, risk) and **Agentic Earned Value** (value layer: cost, rework, outcomes).

Status: use case agreed 27 Oct 2026. Demo data built (`examples/lakeshore/`); the numbers below are the real output of AEV v0.4.0 on that data.

---

## 1. The one-sentence message

> Organizations measure AI **activity** (PRs, tokens, % of code written by agents). Leaders need AI **value**: work that was accepted, stuck, and paid back what it cost.

## 2. The scenario

**Lakeshore Components** (fictional), a mid-size automotive parts supplier in Michigan, is modernizing its **Supplier Quality Portal**: the system suppliers use to submit quality data, corrective actions and shipment certificates.

| | |
|---|---|
| Budget (BAC) | $240,000 over 12 weeks |
| Measured at | end of week 6 |
| Pods | **Portal** (screens, forms, reports) and **Integrations** (ERP and EDI data feeds) |
| AI use | Coding agents open about two-thirds of pull requests in both pods |
| Governance | Program Hub runs status, risks and dashboard from GitHub Issues |
| Value | AEV runs weekly on the same issues |

Why this scenario works for this audience:

- **Great Lakes audience:** manufacturing, automotive and suppliers are the region's home ground. Everyone has lived through a portal or ERP project.
- **Quality language they already use:** *rework*, *scrap*, *first-pass yield*. Rework Rate is "first-pass yield for AI work". This lands without explaining EVM first.
- **Balanced, not hype or doom:** agents are a clear win in one pod and losing money in the other. The lesson is *where* to use them, not *whether*.
- **Infrastructure audience (2027):** the same story told from the cost side: tokens and compute are the small part; human review and rework are the big part.

## 3. The story in four views

The demo moves through four views of the **same program, same week**. Each view is more honest than the one before.

| # | View | What it says | Source |
|---|---|---|---|
| 1 | **AI activity dashboard** | 🟢 "AI is working": 64% of PRs by agents, PR throughput 2.8× baseline, 41M tokens used | Typical vendor/adoption dashboard (we build a simple one) |
| 2 | **Program Hub status** | 🟢 "On track": issues closing ahead of plan, no blockers | Program Hub, from GitHub Issues |
| 3 | **Classic EVM** | 🟢 "Under budget": CPI 1.45, SPI 1.05, forecast $166k | AEV report, Classic column |
| 4 | **Agentic Earned Value** | 🟡 "Over budget, behind schedule": CPI 0.96, SPI 0.88, Rework Rate 15.9%, forecast $250k | AEV report |

Activity numbers in view 1 come from the same data: 45 merged PRs, 64% by agents, 19 issues closed, $6,400 agent spend, 41.8M tokens.

Then the drill-down that turns a number into a decision. Overall, agent work looks fine (CPI **1.05**). **The average hides the problem**; split by Program Hub's teams it does not:

| Team × who did the work | EV | AC | CPI | Why |
|---|---:|---:|---:|---|
| Portal, agent work | $40,000 | $25,000 | **1.60** | Well-specified screens with tests; little rework |
| Portal, human work | $24,000 | $24,000 | 1.00 | Normal |
| Integrations, agent work | $18,000 | $30,000 | **0.60** | Three ERP PRs reverted; review time 4× agent spend |
| Integrations, human work | $24,000 | $26,700 | 0.90 | Normal |

The money line: agent spend is **$6,400**, but agent spend plus human review of it is **$23,400**, and **$20,000** of "done" work was taken back.

**The decision a program leader makes on stage:**

1. Keep agents on Portal work; give them more of it.
2. For Integrations, require contract tests before an issue can be assigned to an agent.
3. Move one reviewer from Portal to Integrations.

**What-if** *(to build in the presenter app)*: the forecast (EAC) moves from about $250k back toward budget.

## 4. Live demo workflow (about 12 minutes)

| Min | Step | What the audience sees | Live or pre-staged |
|---|---|---|---|
| 0–2 | **Hook** | The AI activity dashboard. "Hands up if your leadership has seen a slide like this." | Presenter app |
| 2–4 | **Program Hub** | The real GitHub repo: issues with pods and points, `PROGRAM-DASHBOARD.md` all green. "No spreadsheets: this is generated from GitHub." | Live GitHub |
| 4–6 | **Classic vs. AEV** | Side by side. Same data, two answers. Explain the three changes: agent + review cost, clawback, attribution. | Presenter app |
| 6–9 | **Live moment: rework** | On stage, revert agent PR #66 for issue #22 "Post nonconformance reports (NCR) to ERP" ($8,000). Run the AEV workflow. About 60 seconds later the CPI badge goes from 🟢 **1.03** to 🟡 **0.96**, SPI from 0.95 to 0.88, and #22 shows in "Clawed-back items". Classic EVM does not move (still 1.45). "This is the moment classic EVM never sees." | **Live GitHub**, with a pre-computed fallback in the presenter app |
| 9–11 | **Decision** | Drill-down by pod × authorship. Program Hub's AI briefing writes the executive summary, now including value, rework and the recommendation. | Presenter app + Program Hub AI briefing |
| 11–12 | **Proof and close** | The real pilot (below), the DOI'd method note, "one workflow file, 10 minutes to install". | Slides / GitHub |

### Credibility close: your real pilot

From `GunpreetSabharwall/aev-pilot-sandbox` (real data, small scale, 26 Oct 2026):

- Agent spend (model + CI + tools): **$26.80**
- Human review of that agent work: **$175**, so **$6.53 of review per $1 of agent spend**
- Classic EVM CPI **2.06** vs. AEV CPI **1.64**: classic EVM overstated efficiency by about 25%

Line for the stage: *"The token bill is not the cost of AI. In my own pilot, reviewing the agent's work cost six and a half times what the agent did."*

## 5. Activity metrics vs. value metrics (slide)

| People measure (activity) | Measure instead (value) | AEV indicator |
|---|---|---|
| Number of agent PRs | Value of agent work that was accepted and stuck | EV by authorship class |
| Tokens / model spend | All-in cost: agent + human build + human review | Blended AC, Agent Cost Share |
| "% of code written by AI" | Value earned per $1 spent, by who did it | CPI_A vs. CPI_H |
| PRs merged | Work that stayed merged for 14 days | Rework Rate (clawback) |
| Time saved (self-reported) | Human oversight per $1 of agent spend | Review Load Ratio |
| Velocity | Forecast total cost at current efficiency | EAC |

## 6. What is pending to build

In priority order. Items 1–5 are needed for 10 Nov; 6–7 are nice to have.

| # | Build item | Repo | Why it is needed |
|---|---|---|---|
| 1 | ✅ **Demo dataset**: about 24 issues, 2 pods, 12-week plan, weekly snapshots for weeks 1–6, tuned to the target numbers above | AEV | Current demo has 6 issues and no pods; too thin for a story |
| 2 | ✅ **AEV JSON output** (`aev.json`) with every number in the report, plus a breakdown by pod (from Program Hub pod labels) | AEV | Program Hub and the presenter app need machine-readable results; pod × authorship is the decision view |
| 3 | ✅ **Activity metrics** in the same output: agent PR share, PR count, model spend, tokens | AEV | View 1 must come from the same data, so the contrast is fair |
| 4 | ✅ **Program Hub ⇄ AEV link** (Program-Hub-AI Feature 22): dashboard adds CPI, Rework Rate and badge per initiative; AI PM briefing includes value and rework | Program-Hub-AI | This is what connects the two initiatives |
| 5 | **Presenter app**: one offline HTML page with the four views, a week slider, the drill-down, the "revert" step and the what-if | AEV (`demo/`) | Works with no Wi-Fi; also the fallback if live GitHub is slow |
| 6 | **Live demo repo** seeded by a script: real issues, agent and human PRs, Program Hub + AEV workflows installed, one PR staged to revert on stage | new repo, e.g. `lakeshore-supplier-portal-demo` | Makes the live moment real, not a mock |
| 7 | **Backup video** of the full 12-minute run | – | Standard insurance for any live demo |

## 7. Timeline to 10 November

| Dates | Work |
|---|---|
| 27–30 Oct | Agree this use case. Build items 1–3 (dataset, JSON, activity metrics). |
| 31 Oct–4 Nov | Build items 4–5 (Program Hub link, presenter app). |
| 5–6 Nov | Item 6 (live repo). **Feature freeze 6 Nov.** |
| 7–9 Nov | Rehearse twice end to end, record the backup video, test on venue-like Wi-Fi and a projector. |
| 10 Nov | Talk. |

## 8. Decisions (agreed 27 Oct 2026)

1. **Scenario:** Lakeshore Components / Supplier Quality Portal.
2. **Live GitHub moment:** on stage, live. A screen recording of the full run is the backup.
3. **Slot:** 30 minutes in total; 12 minutes of live demo, the rest slides (introduction, architecture).
4. **Products:** Program Hub AI and AEV stay two separate products and two layers; in the demo they talk to each other through `.aev/aev.json`.

## 9. Demo data at a glance

Built by `examples/lakeshore/build_dataset.py`. Program runs 29 Sep to 22 Dec 2026; week 6 ends on the talk day.

| Week ending | PV | EV | AC | AEV CPI | Classic CPI | Rework Rate |
|---|---:|---:|---:|---:|---:|---:|
| 6 Oct | $20,000 | $14,000 | $17,230 | 0.81 | 0.94 | 0% |
| 13 Oct | $40,000 | $40,000 | $43,700 | 0.92 | 1.11 | 0% |
| 20 Oct | $60,000 | $64,000 | $63,920 | 1.00 | 1.31 | 8.6% |
| 27 Oct | $80,000 | $90,000 | $81,870 | 1.10 | 1.41 | 6.3% |
| 3 Nov | $100,000 | $110,000 | $101,990 | 1.08 | 1.46 | 9.8% |
| 10 Nov (before revert) | $120,000 | $114,000 | $110,400 | 1.03 | 1.45 | 9.5% |
| **10 Nov (after revert)** | **$120,000** | **$106,000** | **$110,400** | **0.96** | **1.45** | **15.9%** |

Classic EVM improves every week. AEV peaks in week 4 and then falls as Integrations rework and review costs build up.
