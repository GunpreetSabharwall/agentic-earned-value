"""Read the two cost files: .aev/hours.csv and .aev/agent-costs.csv.

Bad rows are skipped and reported as warnings; they never stop the run.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

HOUR_TYPES = ("build", "review")
AGENT_CATEGORIES = ("model", "compute", "ci", "tools")


@dataclass
class HoursEntry:
    day: date
    item: Optional[int]
    type: str  # "build" or "review"
    hours: float


@dataclass
class AgentCostEntry:
    day: date
    item: Optional[int]
    category: str  # "model", "compute", "ci" or "tools"
    amount: float


def parse_item(value: str) -> Optional[int]:
    """'12', '#12' -> 12. Blank -> None. Anything else raises ValueError."""
    text = (value or "").strip().lstrip("#").strip()
    if not text:
        return None
    return int(text)


def _parse_amount(value: str) -> float:
    text = (value or "").replace(",", "").replace("$", "").strip()
    return float(text)


def _read_rows(path: Path) -> Tuple[List[dict], List[str]]:
    """Read a CSV into dicts with lower-case, trimmed column names."""
    if not path.exists():
        return [], [f"{path.name} not found; treated as empty."]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            clean = {
                (k or "").strip().lower(): (v or "").strip()
                for k, v in row.items()
            }
            if not any(clean.values()):
                continue  # blank line
            rows.append(clean)
    return rows, []


def load_hours(path: Path) -> Tuple[List[HoursEntry], List[str]]:
    rows, warnings = _read_rows(Path(path))
    entries: List[HoursEntry] = []
    for line_no, row in enumerate(rows, start=2):
        try:
            kind = row.get("type", "").lower()
            if kind not in HOUR_TYPES:
                raise ValueError(f"type must be 'build' or 'review', got {kind!r}")
            hours = _parse_amount(row.get("hours", ""))
            if hours < 0:
                raise ValueError("hours cannot be negative")
            entries.append(
                HoursEntry(
                    day=date.fromisoformat(row.get("date", "")),
                    item=parse_item(row.get("item", "")),
                    type=kind,
                    hours=hours,
                )
            )
        except ValueError as exc:
            warnings.append(f"{Path(path).name} row {line_no} skipped: {exc}.")
    return entries, warnings


def load_agent_costs(path: Path) -> Tuple[List[AgentCostEntry], List[str]]:
    rows, warnings = _read_rows(Path(path))
    entries: List[AgentCostEntry] = []
    for line_no, row in enumerate(rows, start=2):
        try:
            category = row.get("category", "").lower()
            amount = _parse_amount(row.get("amount", ""))
            if amount < 0:
                raise ValueError("amount cannot be negative")
            entries.append(
                AgentCostEntry(
                    day=date.fromisoformat(row.get("date", "")),
                    item=parse_item(row.get("item", "")),
                    category=category,
                    amount=amount,
                )
            )
            if category not in AGENT_CATEGORIES:
                warnings.append(
                    f"{Path(path).name} row {line_no}: unknown category "
                    f"{category!r}; counted as agent cost anyway."
                )
        except ValueError as exc:
            warnings.append(f"{Path(path).name} row {line_no} skipped: {exc}.")
    return entries, warnings
