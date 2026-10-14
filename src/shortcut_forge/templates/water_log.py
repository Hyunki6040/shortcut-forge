"""Template: one-tap water logging to Apple Health with a daily total kept in Stored Content.

Config: {"name": "Water", "sizes_ml": [250, 500], "goal_ml": 2000, "lang": "en" | "ko"}
"""
from __future__ import annotations

from ..builder import Shortcut

EXAMPLE_CONFIG = {"name": "Water", "sizes_ml": [200, 350, 500], "goal_ml": 2000, "lang": "en"}
_T = {"en": ("How much?", "Logged", "Today", "goal"), "ko": ("얼마나 마셨나요?", "기록 완료", "오늘", "목표")}


def build(cfg: dict) -> Shortcut:
    cfg = {**EXAMPLE_CONFIG, **cfg}
    q, done, today, goal = _T[cfg.get("lang", "en")]
    sc = Shortcut(cfg["name"], color="lightblue", glyph=59446)
    sc.set_var("Today", sc.format_date("yyyy-MM-dd"))
    with sc.if_(sc.storage_get("water_date"), "is", "{{Today}}") as br:
        sc.set_var("Total", sc.storage_get("water_total"))
        br.otherwise()
        sc.set_var("Total", "0")
    labels = [f"{ml} mL" for ml in cfg["sizes_ml"]]
    with sc.menu(q, labels) as m:
        for ml, label in zip(cfg["sizes_ml"], labels):
            with m.case(label):
                sc.set_var("Amount", str(ml))
    sc.health_log("Water", "{{Amount}}", "mL")
    total = sc.math("{{Total}}", "+", "{{Amount}}")
    sc.storage_set("water_total", total)
    sc.storage_set("water_date", "{{Today}}")
    sc.notify(f"💧 {done} {{{{Amount}}}} mL", f"{today}: {total} / {cfg['goal_ml']} mL {goal}")
    return sc
