"""Ready-made shortcut generators. Each template exposes build(config) -> Shortcut and EXAMPLE_CONFIG."""
from __future__ import annotations

from . import supplement_tracker, water_log

TEMPLATES = {
    "supplement-tracker": supplement_tracker,
    "water-log": water_log,
}


def get(name: str):
    try:
        return TEMPLATES[name]
    except KeyError as e:
        raise ValueError(f"unknown template {name!r}; available: {', '.join(TEMPLATES)}") from e
