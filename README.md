# Agentic Earned Value (AEV)

[![DOI](https://zenodo.org/badge/1398771857.svg)](https://doi.org/10.5281/zenodo.23071416)
[![Tests](https://github.com/GunpreetSabharwall/agentic-earned-value/actions/workflows/tests.yml/badge.svg)](https://github.com/GunpreetSabharwall/agentic-earned-value/actions/workflows/tests.yml)

**Earned Value Management for software programs where AI agents do part of the work.**

AEV was first defined by Gunpreet Sabharwall (ORCID [0009-0000-5434-7382](https://orcid.org/0009-0000-5434-7382)), 2026.

Classic EVM assumes people do the work. When AI agents write code, new costs (model usage, compute, human review) and new risks (work that gets reverted) appear. AEV keeps CPI, SPI and EAC, and adds:

1. **Blended Actual Cost:** agent and review costs included
2. **Rework-adjusted Earned Value:** value taken back if work is reverted
3. **Attribution:** efficiency by human, agent, or mixed work

📄 Method note: [AEV-method-note-v0.1.md](AEV-method-note-v0.1.md)

## Status

- v0.1: method definition.
- v0.2.0: reference GitHub Action. Add one workflow file to any public repository and get a weekly `AEV-REPORT.md` and a CPI badge.
- **v0.3.0: better authorship detection.** Agent work is recognised even when the agent opens pull requests under a person's account. See [How authorship is detected](#how-authorship-is-detected) and [CHANGELOG.md](CHANGELOG.md).

---

## Try it in 1 minute (no GitHub setup needed)

The demo runs on sample data in [`examples/demo/`](examples/demo/) and reproduces the worked example in section 5 of the method note.

You need Python 3.11 or newer. In a terminal, from the top folder of this repository:

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m aev --demo
```

The report is printed and saved to `examples/demo/AEV-REPORT.md`. You can also just [read the saved demo report](examples/demo/AEV-REPORT.md).

---

## Quick start: add AEV to your repository

You do this once. It takes about 10 minutes and all of it can be done in the GitHub website.

### Step 1: Copy one workflow file

In your repository, create the file **`.github/workflows/aev.yml`** with exactly this content (also in [`examples/aev.yml`](examples/aev.yml)):

```yaml
name: AEV report

on:
  schedule:
    - cron: "17 6 * * 1"   # every Monday at 06:17 UTC
  workflow_dispatch:        # adds a "Run workflow" button on the Actions tab

permissions:
  contents: write           # to commit AEV-REPORT.md and .aev/badge.json
  issues: read              # to read issue labels and history
  pull-requests: read       # to read linked pull requests

jobs:
  aev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: GunpreetSabharwall/agentic-earned-value@v0.3.0
```

No password or personal token is needed. GitHub gives the workflow a temporary token automatically.

### Step 2: Add the settings folder

Create a folder called **`.aev`** at the top of your repository with three files. You can copy them from [`examples/starter/.aev/`](examples/starter/.aev/).

**`.aev/config.yml`**: your budget and plan

```yaml
budget_at_completion: 100000   # total planned budget for the work (money)
value_per_point: 1000          # an issue labelled "aev-points:3" is worth 3 x this
start_date: 2026-01-05         # planned value starts at 0 on this date (YYYY-MM-DD)...
end_date: 2026-03-16           # ...and reaches the full budget on this date
hourly_rate: 100               # cost of one hour of human time (money)
stabilization_window_days: 14  # work reopened or reverted within this many days is taken back
agent_accounts:                # GitHub logins of your AI agents / bots
  - my-coding-agent[bot]
  - claude
# agent_label: aev-agent       # optional: pull requests with this label always count as agent work
```

`agent_accounts` lists the GitHub logins of your AI agents. Upper/lower case and the `[bot]` ending do not matter. If you are not sure what login your agent uses, open one of its commits on GitHub and look at the author name shown there.

**`.aev/hours.csv`**: human time. One line per entry. `item` is the issue number (or leave it blank). `type` is `build` (doing the work) or `review` (reviewing or correcting agent work).

```csv
date,item,type,hours
2026-01-12,14,build,6
2026-01-13,15,review,1.5
2026-01-13,,review,2
```

**`.aev/agent-costs.csv`**: money spent on agents. `category` is one of `model`, `compute`, `ci`, `tools`.

```csv
date,item,category,amount
2026-01-12,15,model,42.50
2026-01-31,,ci,120
```

You can edit these CSV files in the GitHub website or in any spreadsheet program (save as CSV).

### Step 3: Label your issues

Give each issue a label **`aev-points:N`**, where N is its size in points. For example `aev-points:3`. The issue's budgeted value is N × `value_per_point`.

To create labels: go to your repository → **Issues** → **Labels** → **New label**, and create, for example, `aev-points:1`, `aev-points:2`, `aev-points:3`, `aev-points:5`, `aev-points:8`.

Link each pull request to its issue, for example by writing `Fixes #14` in the pull request description.

### Step 4: Run it

Go to **Actions** → **AEV report** → **Run workflow**. After about a minute, `AEV-REPORT.md` appears at the top of your repository. After that it updates every Monday by itself.

### Optional: show the CPI badge

Add this line to your README, replacing `OWNER/REPO` with your repository:

```markdown
![AEV CPI](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/.aev/badge.json)
```

The badge is green when CPI is 1.00 or more, yellow from 0.90 to 0.99, and red below 0.90.

### Action options

All are optional.

| Option | Default | What it does |
|---|---|---|
| `config` | `.aev/config.yml` | Where your settings file is. The CSV files are read from the same folder. |
| `output` | `AEV-REPORT.md` | Where the report is written. |
| `badge` | `.aev/badge.json` | Where the badge file is written. |
| `commit` | `true` | Set to `false` to skip committing the report (it still appears in the workflow run summary). |
| `demo` | `false` | Set to `true` to run on the sample data instead of your repository. |

Example: `with: { commit: "false" }` under the `uses:` line.

---

## How AEV is calculated

The full definition is in the [method note](AEV-method-note-v0.1.md). In short:

| Term | How this tool gets it |
|---|---|
| **PV** (planned value) | Grows in a straight line from 0 on `start_date` to `budget_at_completion` on `end_date`. |
| **Accepted** | Issue closed as *completed* **and** at least one linked pull request merged. |
| **Clawback** | An accepted issue is reopened, or one of its pull requests is reverted, within `stabilization_window_days` of acceptance. |
| **EV** | Gross EV (value of accepted issues) − Clawback. |
| **AC** | AC_build (build hours × rate) + AC_review (review hours × rate) + AC_agent (agent costs). |
| **CPI, SPI, EAC** | EV / AC, EV / PV, AC + (BAC − EV) / CPI. |
| **Rework Rate** | Clawback / Gross EV. |
| **Agent Cost Share** | AC_agent / AC. |
| **Review Load Ratio** | AC_review / AC_agent. |
| **Authorship class** | Each merged pull request is classed as agent, human or mixed (see [How authorship is detected](#how-authorship-is-detected)). An issue is **A** if all its pull requests are agent work, **H** if all are human work, **M** otherwise. CPI is shown for each class. |

If a number cannot be calculated (for example, CPI when nothing has been spent yet), the report shows **n/a**.

The report also shows a **Classic EVM** column (build labor only, no clawback) next to AEV, so you can see what classic EVM would have told you.

### How authorship is detected

Some coding agents open pull requests under the account of the person who started them, but write the commits under their own account (for example, the login `claude`). So AEV looks at more than the pull request's author. Each merged pull request linked to an issue is checked with these rules, in order:

1. **The pull request has the label `aev-agent`** → agent work. This is a **manual override**: add the label on GitHub whenever an agent did the work but AEV would not otherwise see it. You can use a different label name with the optional `agent_label` setting in `.aev/config.yml`.
2. **The pull request was opened by an account in `agent_accounts`** → agent work.
3. **Otherwise, AEV looks at every commit** in the pull request, including co-authors (the `Co-authored-by:` lines that many agents add to commit messages):
   - every commit has an agent author or co-author → **agent** work
   - some commits do and some do not → **mixed** work
   - no commit does → **human** work

Matching ignores upper/lower case and the `[bot]` ending. A commit whose author is not linked to any GitHub account counts as agent work only if its author email or name is written exactly as in `agent_accounts`. Otherwise it counts as human.

An issue is then **A** if all its pull requests are agent work, **H** if all are human work, and **M** in every other case (so a single mixed pull request makes the issue mixed).

### How the code is organised

| Folder / file | What is in it |
|---|---|
| `action.yml` | The GitHub Action other repositories use. |
| `src/aev/formulas.py` | Every AEV formula, one small function each. |
| `src/aev/items.py` | Rules for accepted, clawback and authorship class. |
| `src/aev/calculator.py` | Puts the formulas together. |
| `src/aev/github_data.py` | Reads issues and pull requests from GitHub (the only part that talks to GitHub). |
| `src/aev/report.py` | Writes `AEV-REPORT.md` and the badge. |
| `tests/` | Automated tests, including the method note's worked example. |
| `examples/` | Demo data, starter settings and the workflow file to copy. |

To run the tests: `pip install -r requirements-dev.txt` then `python -m pytest`.

---

## Limitations

- **Costs are entered by hand in v0.1.** Hours and agent costs come from `.aev/hours.csv` and `.aev/agent-costs.csv`. There is no automatic import from billing or time-tracking tools yet.
- **Review time is self-reported.** AC_review is only as accurate as the hours people record.
- **"Required checks passed" is not checked separately.** A merged pull request is taken as having passed its checks. Use branch protection if you need that guarantee.
- **Reverts are found by GitHub's standard "Revert" button text** (`Reverts owner/repo#123`). Reverts made by hand in other ways are not detected; reopening the issue still triggers a clawback.
- **Planned value is a straight line** between the start and end dates.
- **Only the first 100 commits of a pull request are checked for authorship.** Very large pull requests get a note in the report's "Data notes" section.
- **Public repositories** are the target. Private repositories work too, as long as the workflow has the permissions shown above.
- If your default branch is protected so that workflows cannot push, set `commit: "false"`. The report is still shown in each workflow run's summary.
- The example numbers are illustrative. See section 7 of the method note for the method's own limitations.

---

## Cite

See "Cite this repository" in the sidebar, or [CITATION.cff](CITATION.cff).

## License

Method note and docs: CC BY 4.0. Code: Apache 2.0 (see [LICENSE](LICENSE)).
