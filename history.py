"""
research_agent/history.py
==========================
Persistent research history cache stored as JSON.

- Each entry is keyed by a normalised topic string.
- On cache hit, the full AgentState is restored — no LLM or web calls needed.
- History file: research_history.json (next to this file).
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "research_history.json")


# ---------------------------------------------------------------------------
# Key normalisation — makes lookup case/whitespace insensitive
# ---------------------------------------------------------------------------

def _normalise(topic: str) -> str:
    return re.sub(r"\s+", " ", topic.strip().lower())


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _load() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get(topic: str) -> Optional[dict]:
    """Return cached entry for topic, or None if not found."""
    return _load().get(_normalise(topic))


def save(topic: str, state_dict: dict) -> None:
    """Persist a completed AgentState dict under the normalised topic key."""
    data = _load()
    data[_normalise(topic)] = {
        **state_dict,
        "cached_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "original_topic": topic.strip(),
    }
    _save(data)


def all_entries() -> list[dict]:
    """Return all history entries sorted newest first."""
    data = _load()
    entries = list(data.values())
    entries.sort(key=lambda e: e.get("cached_at", ""), reverse=True)
    return entries


def delete(topic: str) -> bool:
    """Delete a history entry. Returns True if it existed."""
    data = _load()
    key = _normalise(topic)
    if key in data:
        del data[key]
        _save(data)
        return True
    return False


def clear_all() -> None:
    """Wipe the entire history file."""
    _save({})
