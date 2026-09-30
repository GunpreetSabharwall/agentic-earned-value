# Changelog

All notable changes to this project are listed here.

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
