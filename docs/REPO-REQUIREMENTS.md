# What a repository needs for AEV to measure it

AEV can measure **any GitHub repository** it has a token for. Nothing has to be installed in that repository: AEV reads it from outside, through the GitHub API, and writes its results wherever you run it (for example into Program Hub). This page lists what the repository must contain, and how the team must work in it, for the numbers to be right.

AEV only **reads** the measured repository. It never writes to it.

## Quick checklist

| # | Required | How | Why AEV needs it |
|---|---|---|---|
| 1 | **Work is tracked as GitHub Issues** | One issue per piece of planned work | Issues are the work items that earn value |
| 2 | **Each planned issue has a size label** | `aev-points:N`, for example `aev-points:3` | Budgeted value = N × `value_per_point`. Issues without it earn nothing and are ignored |
| 3 | **Every pull request names its issue** | In the PR description: `Fixes #12` (finishes it) or `Part of #12` (partial work) | Links cost and authorship to the issue. A PR that names no issue is not counted |
| 4 | **Finished issues are closed as completed** | Merging a `Fixes #12` PR does this; or close it by hand as *Completed* | Accepted = closed as completed **and** at least one linked PR merged. *Closed as not planned* never earns |
| 5 | **Undo work with GitHub's Revert button, or reopen the issue** | PR page → *Revert*, then merge the revert PR | AEV detects `Reverts owner/repo#N` and reopen events, and takes the value back within the stabilization window |
| 6 | **Agent work is recognisable** | Any one of: PR label `aev-agent` · the PR opened by an agent account · commits authored or co-authored (`Co-authored-by:`) by an agent account | Splits value and cost into agent, human and mixed work |

## Optional

| What | How | What you get |
|---|---|---|
| Team labels | One label per team on each issue, for example `pod-portal`, and the same names in AEV's `teams` setting (Program Hub uses its pod labels) | Results by team × who did the work |
| Merge into the default branch | Normal GitHub flow | GitHub's own issue links work too; AEV also reads `Fixes` / `Part of` from PR descriptions, so other bases still count |

## Kept outside the measured repository

These belong to whoever runs AEV (a PMO, finance, or Program Hub), not to the engineering team, and can live in any folder:

| File | What it holds | Who usually owns it |
|---|---|---|
| `config.yml` | Budget, `value_per_point`, plan start and end dates, hourly rate, stabilization window, agent accounts, teams | Program manager |
| `hours.csv` | Human hours per issue: `date,item,type,hours` with `type` = `build` or `review` | Team leads (weekly) |
| `agent-costs.csv` | Agent spend per issue: `date,item,category,amount[,tokens]` with `category` = `model`, `compute`, `ci` or `tools` | Finance or platform team (from billing exports) |

`item` is the issue number in the measured repository. Leave it blank for costs that belong to no single issue.

## Access

| Measured repository | Token AEV needs |
|---|---|
| The repository the workflow runs in | Nothing to set up: the built-in `GITHUB_TOKEN` |
| Any other repository, public or private | A token that can **read** it. Recommended: a fine-grained personal access token (or GitHub App) with read-only *Contents*, *Issues*, *Pull requests* and *Metadata* on the repositories to measure, stored as a secret (Program Hub calls it `OCTO_PAT`) |

## Running it

```bash
# From anywhere, on any repository
GITHUB_TOKEN=<token> PYTHONPATH=src python -m aev \
  --repo owner/name \
  --config path/to/config.yml \
  --hours path/to/hours.csv --agent-costs path/to/agent-costs.csv \
  --output AEV-REPORT.md --json aev.json --badge badge.json
```

```yaml
# As a GitHub Action in a central repository (for example Program Hub)
- uses: GunpreetSabharwall/agentic-earned-value@v0.4.0
  with:
    repo: my-org/supplier-portal              # the repository to measure
    config: initiatives/supplier-portal/aev/config.yml
    output: initiatives/supplier-portal/AEV-REPORT.md
    json: initiatives/supplier-portal/aev.json
    badge: initiatives/supplier-portal/aev-badge.json
    github-token: ${{ secrets.OCTO_PAT }}
```

AEV can still run inside the measured repository itself (the original set-up in the README), reading its own `.aev/` folder.

## Common mistakes

| Symptom in the report | Cause |
|---|---|
| An issue you finished earns nothing | No `aev-points:N` label, closed as *not planned*, or no merged PR names it |
| Agent work shows as human | The agent opens PRs under a person's account and its commits are not co-authored: add the `aev-agent` label |
| A revert is not taken back | The revert was a hand-written commit, not GitHub's Revert button (reopen the issue instead), or it came after the stabilization window |
| Costs counted as "Unassigned" | The `item` column is blank or names an issue that does not exist |
