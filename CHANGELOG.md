# Changelog

All notable changes to this project are listed here.

## [0.4.0] - 2026-10-27

### Added

- **Results by team.** Optional `teams` setting in `.aev/config.yml` maps a team name to an issue label (for example the pod labels Program Hub uses). The report gets a "By team" table with EV, AC and CPI for each team, split by authorship class.
- **AI activity vs. value.** A new report section puts what AI dashboards usually count (merged PRs, share by agents, issues closed, agent spend) next to what AEV counts (work that stuck, CPI of agent work, Rework Rate, agent plus review cost).
- **Optional `tokens` column** in `.aev/agent-costs.csv`.
- **JSON output.** Every result is written to `.aev/aev.json` (schema `aev-results/1`), so other tools such as Program Hub can read AEV without parsing the report. New `--json` option and `json` Action input; the Action commits the file with the report.
- **Lakeshore example** in `examples/lakeshore/`: a fictional 12-week, two-team program with weekly results, built by `build_dataset.py`.

### Changed

- The workflow file to copy now uses `@v0.4.0`.

## [0.3.1] - 2026-10-07

### Fixed

- Small costs are no longer rounded away in the report's "Where the numbers come from" table: amounts with cents now show them (for example $0.50 instead of $0). Headline figures are still shown in whole dollars.
- Hours in that table now show up to two decimals (7.75 h instead of 7.8 h).

### Changed

- The workflow file to copy now uses `@v0.3.1`.

## [0.3.0] - 2026-10-05

### Added

- Better authorship detection. Each merged pull request is now classed as agent, human or mixed using, in order: the `aev-agent` label (a manual override), the pull request author, then the authors and co-authors of every commit. This recognises agents that open pull requests under a person's account but commit under their own login.
- Optional `agent_label` setting in `.aev/config.yml` to use a different label name (default `aev-agent`).
- A report note when a pull request has more than 100 commits (only the first 100 are checked).

### Changed

- An issue is now **M** (mixed) if any of its pull requests is mixed, as well as when it has both agent and human pull requests.
- Updated `actions/checkout` to v5 and `actions/setup-python` to v6 (newer Node.js runtime).
- The workflow file to copy now uses `@v0.3.0`.

## [0.2.0] - 2026-09-30

First release of the AEV reference tool, implementing method note v0.1.

### Added

- Reusable GitHub Action (`action.yml`). Add one workflow file to a repository to get a weekly `AEV-REPORT.md` and a CPI badge (`.aev/badge.json`, shields.io format). Runs on a schedule and on demand, and commits the report back.
- Calculation of PV, EV (with rework clawback), blended AC, CPI, SPI, EAC, Rework Rate, Agent Cost Share, Review Load Ratio, and CPI per authorship class (A, H, M).
- Classic EVM vs. AEV comparison and a plain-English "what this means" line in the report.
- Inputs: `.aev/config.yml`, `aev-points:N` issue labels, `.aev/hours.csv`, `.aev/agent-costs.csv`.
- Demo mode (`python -m aev --demo`) that runs on sample data without GitHub and reproduces the method note's worked example.
- Unit tests for every formula, including the section 5 worked example, and a test workflow that runs on every pull request.

## [0.1] - 2026-09-30

- First public definition of AEV (method note).
