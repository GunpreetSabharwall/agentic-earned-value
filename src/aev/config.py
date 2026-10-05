"""Read and check .aev/config.yml."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import yaml


class ConfigError(ValueError):
    """Raised when the config file is missing or has a bad value."""


@dataclass
class Config:
    budget_at_completion: float
    value_per_point: float
    start_date: date
    end_date: date
    hourly_rate: float
    stabilization_window_days: int = 14
    agent_accounts: List[str] = field(default_factory=list)
    # Optional. Fixes the "as of" date (useful for demos and tests).
    # When not set, today's date is used.
    as_of_date: Optional[date] = None
    # Optional. Pull requests with this label always count as agent work.
    agent_label: str = "aev-agent"
    currency_symbol: str = "$"


def _to_number(raw: dict, key: str, allow_zero: bool = False) -> float:
    if key not in raw or raw[key] is None:
        raise ConfigError(f"'{key}' is missing from the config file.")
    value = raw[key]
    if isinstance(value, str):
        value = value.replace(",", "").replace("$", "").strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ConfigError(f"'{key}' must be a number, got {raw[key]!r}.")
    if number < 0 or (number == 0 and not allow_zero):
        raise ConfigError(f"'{key}' must be greater than zero, got {raw[key]!r}.")
    return number


def _to_date(raw: dict, key: str, required: bool = True) -> Optional[date]:
    value = raw.get(key)
    if value is None:
        if required:
            raise ConfigError(f"'{key}' is missing from the config file.")
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ConfigError(f"'{key}' must be a date like 2026-01-31, got {value!r}.")


def parse_config(raw: dict) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("The config file must contain 'key: value' lines.")

    start = _to_date(raw, "start_date")
    end = _to_date(raw, "end_date")
    if end <= start:
        raise ConfigError("'end_date' must be after 'start_date'.")

    window = raw.get("stabilization_window_days", 14)
    try:
        window = int(window)
    except (TypeError, ValueError):
        raise ConfigError("'stabilization_window_days' must be a whole number.")
    if window < 0:
        raise ConfigError("'stabilization_window_days' cannot be negative.")

    accounts = raw.get("agent_accounts") or []
    if isinstance(accounts, str):
        accounts = [accounts]
    if not isinstance(accounts, list):
        raise ConfigError("'agent_accounts' must be a list of GitHub logins.")

    return Config(
        budget_at_completion=_to_number(raw, "budget_at_completion"),
        value_per_point=_to_number(raw, "value_per_point"),
        start_date=start,
        end_date=end,
        hourly_rate=_to_number(raw, "hourly_rate", allow_zero=True),
        stabilization_window_days=window,
        agent_accounts=[str(a).strip() for a in accounts if str(a).strip()],
        as_of_date=_to_date(raw, "as_of_date", required=False),
        agent_label=str(raw.get("agent_label") or "aev-agent").strip(),
        currency_symbol=str(raw.get("currency_symbol", "$")),
    )


def load_config(path: Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return parse_config(raw)
