"""Read-only access to the files the ML pipeline already exports.

The dashboard day and real-day anomalies come from ``har.export_dashboard`` /
``har.export_anomalies`` (``src/data/homes/generated/``); the live-demo scenarios
from ``har.replay`` (``public/replay/``). The API serves them as they are, so the
frontend can switch from bundled JSON to API calls without the data changing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from har.data import DATASETS, ML_DIR

ROOT = ML_DIR.parent
GENERATED_DIR = ROOT / "src" / "data" / "homes" / "generated"
REPLAY_DIR = ROOT / "public" / "replay"


class NotFound(LookupError):
    """A requested home, scenario or file does not exist."""


def check_home(home: str) -> str:
    if home not in DATASETS:
        raise NotFound(f"unknown home '{home}'; known: {', '.join(DATASETS)}")
    return home


@lru_cache(maxsize=64)
def _read(path: Path, mtime: float) -> dict:
    # mtime is part of the cache key, so re-exported files are picked up.
    return json.loads(path.read_text(encoding="utf8"))


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise NotFound(f"{path.relative_to(ROOT).as_posix()} has not been exported yet")
    return _read(path, path.stat().st_mtime)


def dashboard_day(home: str) -> dict:
    return read_json(GENERATED_DIR / f"{check_home(home)}.json")


def anomalies(home: str) -> dict:
    return read_json(GENERATED_DIR / f"{check_home(home)}-anomalies.json")


def replay_index() -> dict:
    return read_json(REPLAY_DIR / "index.json")


def scenario(home: str, scenario_id: str) -> dict:
    """One replay scenario. The id is looked up in the index, never used as a path."""
    entry = replay_index().get(check_home(home))
    if entry is None:
        raise NotFound(f"no replay scenarios exported for '{home}'")
    for sc in entry["scenarios"]:
        if sc["id"] == scenario_id:
            return read_json(REPLAY_DIR / sc["file"])
    ids = ", ".join(sc["id"] for sc in entry["scenarios"])
    raise NotFound(f"unknown scenario '{scenario_id}' for {home}; known: {ids}")
