"""Template: multi-user supplement tracker with Apple Health logging and self-maintaining reminders.

What the generated shortcut does (iOS 27):
- First run asks who uses this device and whether to manage reminders; settings live in Stored Content.
- Shows today's slots with state: "✓ done", "▶ now", "missed" (so a forgotten lunch can still be logged at night).
- Logs every nutrient of the slot to Apple Health (mcg converted to mg), keeps a 50-entry history.
- Completes today's reminder for that slot and creates tomorrow's reminders for *all* slots, skipping
  any that already exist (idempotent, searched by a fixed phrase).
- "Weekly report" asks Apple Intelligence (Use Model) to summarise the last 7 days.
- Settings menu: switch user, reminders on/off, per-slot reminder time, show settings, wipe data.

Config (JSON):
{
  "name": "Supplement Check", "lang": "en" | "ko", "word": "supplements",
  "users": {
    "Alex": {"emoji": "🩵", "slots": [
      {"id": "morning", "label": "Morning", "emoji": "🌅", "time": "08:00", "window": [0, 11],
       "items": ["Probiotic 1 cap"], "nutrients": {"Vitamin D": 25}, "note": "after breakfast"}
    ]}
  }
}
"""
from __future__ import annotations

import copy
from typing import Any

from ..builder import Shortcut
from ..refs import var

STRINGS = {
    "en": {
        "who": "First run: whose supplements does this device log?", "rem_q": "Manage reminders automatically?",
        "on": "On", "off": "Off", "setup_done": "Setup complete", "setup_hint": "Change anything later in ⚙ Settings",
        "done": "done today", "now": "now", "missed": "log missed", "report": "📊 7-day report",
        "settings": "⚙ Settings", "reset": "↺ Reset today", "reset_done": "Today's checks cleared",
        "reset_hint": "Values already in Health stay there", "again": "Already logged today. Log again?",
        "again_yes": "Log again", "cancel": "Cancel", "logged": "logged", "today": "Today",
        "no_history": "No history yet. Log for a few days first.",
        "report_prompt": ("You are a supplement-adherence coach. Plan (JSON) and history follow. Using only the last "
                          "7 days including today, write at most 8 lines: 1) days taken per slot (e.g. Lunch 6/7) "
                          "2) missed dates 3) one improvement for next week. Do not guess and give no medical advice."),
        "user": "Switch user", "reminders": "Reminders on/off", "times": "Reminder times", "show": "Show settings",
        "wipe": "Wipe all data", "wipe_q": "Delete today's log and history? (Health and Reminders stay)",
        "wipe_yes": "Delete", "wiped": "Data wiped", "saved": "Settings saved", "time_q": "reminder time (HH:mm)",
        "which": "Which slot?", "current": "Current: ",
    },
    "ko": {
        "who": "처음 설정이에요. 이 기기는 누구의 영양제를 기록하나요?", "rem_q": "미리알림을 자동으로 관리할까요?",
        "on": "켜기", "off": "끄기", "setup_done": "설정 완료", "setup_hint": "⚙ 설정에서 언제든 바꿀 수 있어요",
        "done": "오늘 기록함", "now": "지금", "missed": "놓친 것 기록", "report": "📊 최근 7일 리포트",
        "settings": "⚙ 설정", "reset": "↺ 오늘 체크 초기화", "reset_done": "오늘 체크 초기화",
        "reset_hint": "건강 앱에 들어간 값은 건강 앱에서 지워야 해요", "again": "오늘 이미 기록했어요. 한 번 더 기록할까요?",
        "again_yes": "한 번 더 기록", "cancel": "취소", "logged": "기록 완료", "today": "오늘",
        "no_history": "아직 기록이 없어요. 며칠 기록한 뒤 다시 실행해 주세요.",
        "report_prompt": ("너는 영양제 복용 코치야. 아래 계획(JSON)과 기록을 보고 오늘 포함 최근 7일만 8줄 이내로 정리해. "
                          "1) 시간대별 복용 일수 (예: 점심 6/7) 2) 빠뜨린 날짜 3) 다음 주 개선점 하나. 추측하지 말고 의학적 판단은 하지 마."),
        "user": "사용자 변경", "reminders": "미리알림 켜기/끄기", "times": "미리알림 시각", "show": "현재 설정 보기",
        "wipe": "기록 전체 삭제", "wipe_q": "오늘기록·이력을 모두 지울까요? (건강 앱·미리알림은 그대로)",
        "wipe_yes": "모두 삭제", "wiped": "기록 삭제", "saved": "설정 저장", "time_q": "미리알림 시각 (HH:mm)",
        "which": "어느 시간대?", "current": "현재: ",
    },
}

HISTORY_MAX = 50
SCHEMA = "1"


def validate_config(cfg: dict) -> dict:
    cfg = copy.deepcopy(cfg)
    if not cfg.get("users"):
        raise ValueError("config.users must have at least one user")
    cfg.setdefault("name", "Supplement Check")
    cfg.setdefault("lang", "en")
    cfg.setdefault("word", "supplements" if cfg["lang"] == "en" else "영양제")
    if cfg["lang"] not in STRINGS:
        raise ValueError(f"lang must be one of {sorted(STRINGS)}")
    for uname, u in cfg["users"].items():
        if not u.get("slots"):
            raise ValueError(f"user {uname!r} needs slots")
        u.setdefault("emoji", "💊")
        ids = set()
        for s in u["slots"]:
            for k in ("id", "label"):
                if not s.get(k):
                    raise ValueError(f"user {uname!r}: every slot needs {k!r}")
            if s["id"] in ids:
                raise ValueError(f"user {uname!r}: duplicate slot id {s['id']!r}")
            ids.add(s["id"])
            s.setdefault("emoji", "💊")
            s.setdefault("time", "09:00")
            s.setdefault("window", [0, 24])
            s.setdefault("items", [])
            s.setdefault("nutrients", {})
            s.setdefault("note", "")
    # a label must not be a substring of another label of the same user (selection matching)
    for uname, u in cfg["users"].items():
        labels = [s["label"] for s in u["slots"]]
        for a in labels:
            for b in labels:
                if a != b and (a + " ·") in (b + " ·"):
                    raise ValueError(f"user {uname!r}: slot label {a!r} is contained in {b!r}; rename one")
    return cfg


def build(cfg: dict) -> Shortcut:
    cfg = validate_config(cfg)
    T = STRINGS[cfg["lang"]]
    word = cfg["word"]
    users = list(cfg["users"])
    sc = Shortcut(cfg["name"], color=cfg.get("color", "teal"), glyph=cfg.get("glyph", 59511))

    plan = {u: {s["id"]: {k: s[k] for k in ("label", "items", "nutrients", "note", "time")}
                for s in cfg["users"][u]["slots"]} for u in users}
    all_types = sorted({t for u in users for s in cfg["users"][u]["slots"] for t in s["nutrients"]})

    sc.comment(f"{cfg['name']} — generated by shortcut-forge (iOS 27+).\n"
               "Edit the plan JSON below to change products or doses. Health types are fixed at build time.")
    sc.set_var("Plan", sc.dictionary(plan))

    # dates
    sc.set_var("Today", sc.format_date("yyyy-MM-dd"))
    sc.set_var("TodayShort", sc.format_date("M/d"))
    sc.set_var("Hour", sc.number(sc.format_date("H")))
    tmr = sc.adjust_date(1, "days")
    sc.set_var("Tomorrow", sc.format_date("yyyy-MM-dd", tmr))
    sc.set_var("TomorrowShort", sc.format_date("M/d", tmr))

    # schema migration: wipe without reading (old values may be unreadable)
    with sc.if_(sc.storage_get("schema"), "is", SCHEMA) as br:
        br.otherwise()
        for k in ("env", "date", "today", "history"):
            sc.storage_wipe(k)
        sc.storage_set("schema", SCHEMA)

    # env / first run
    env_raw = sc.storage_get("env")
    with sc.if_(env_raw, "has any value") as br:
        sc.set_var("Env", sc.to_dict(env_raw))
        br.otherwise()
        with sc.menu(T["who"], users) as m:
            for u in users:
                with m.case(u):
                    sc.set_var("NewUser", u)
        with sc.menu(T["rem_q"], [T["on"], T["off"]]) as m:
            with m.case(T["on"]):
                sc.set_var("NewRem", "on")
            with m.case(T["off"]):
                sc.set_var("NewRem", "off")
        sc.set_var("Env", sc.dictionary({}))
        sc.set_value("Env", "user", "{{NewUser}}")
        sc.set_value("Env", "reminders", "{{NewRem}}")
        sc.storage_set("env", "{{Env}}")
        sc.notify(T["setup_done"], T["setup_hint"])
    sc.set_var("User", sc.get_value("{{Env}}", "user"))
    sc.set_var("Reminders", sc.get_value("{{Env}}", "reminders"))

    # today's log (cleared when the date changes)
    with sc.if_(sc.storage_get("date"), "is", "{{Today}}") as br:
        sc.set_var("Log", sc.storage_get("today"))
        br.otherwise()
        sc.storage_delete("today")
        sc.set_var("Log", "")

    # menu list with per-slot state
    def per_user(fn):
        """Emit fn(user) under an If chain on {{User}} (build-time unrolling, runtime dispatch)."""
        def chain(i: int):
            if i == len(users) - 1:
                fn(users[i])
                return
            with sc.if_("{{User}}", "is", users[i]) as br:
                fn(users[i])
                br.otherwise()
                chain(i + 1)
        chain(0)

    def list_for(u: str):
        for s in cfg["users"][u]["slots"]:
            summary = ", ".join(s["items"])[:60] or s["label"]
            lo, hi = s["window"]
            with sc.if_("{{Log}}", "contains", f"[{s['id']}]") as br:
                sc.append_var("Choices", f"✓ {s['label']} · {T['done']}")
                br.otherwise()
                with sc.if_("{{Hour}}", "<", lo) as b2:
                    sc.append_var("Choices", f"{s['label']} · {summary}")
                    b2.otherwise()
                    with sc.if_("{{Hour}}", "<", hi) as b3:
                        sc.append_var("Choices", f"▶ {s['label']} · {summary} · {T['now']}")
                        b3.otherwise()
                        sc.append_var("Choices", f"{s['label']} · {summary} · {T['missed']}")

    per_user(list_for)
    for extra in (T["report"], T["settings"], T["reset"]):
        sc.append_var("Choices", extra)
    sc.set_var("Picked", sc.choose_from_list("{{Choices}}", "{{User}} · {{Today}}"))

    # ---- branches
    with sc.if_("{{Picked}}", "is", T["reset"]) as br_reset:
        sc.storage_delete("today")
        sc.notify(T["reset_done"], T["reset_hint"])
        br_reset.otherwise()
        with sc.if_("{{Picked}}", "is", T["report"]) as br_rep:
            hist = sc.storage_get("history")
            with sc.if_(hist, "has any value") as b:
                plan_txt = sc.get_value("{{Plan}}", "{{User}}", split_path=False)
                resp = sc.ask_llm(f"{T['report_prompt']}\n\n{T['today']}: {{{{Today}}}}\n\n{plan_txt}\n\n{hist}")
                sc.show(resp)
                b.otherwise()
                sc.show(T["no_history"])
            br_rep.otherwise()
            with sc.if_("{{Picked}}", "is", T["settings"]) as br_set:
                _settings(sc, cfg, T, users)
                br_set.otherwise()
                per_user(lambda u: _record(sc, cfg, T, u, word, all_types))
    return sc


def _settings(sc: Shortcut, cfg: dict, T: dict, users: list[str]) -> None:
    def save(msg: str):
        sc.storage_set("env", "{{Env}}")
        sc.notify(T["saved"], msg)

    items = [T["user"], T["reminders"], T["times"], T["show"], T["wipe"]]
    with sc.menu(T["settings"], items) as m:
        with m.case(T["user"]):
            with sc.menu(T["user"], users) as mu:
                for u in users:
                    with mu.case(u):
                        sc.set_value("Env", "user", u)
                        sc.storage_delete("today")
                        save(u)
        with m.case(T["reminders"]):
            with sc.menu(T["current"] + "{{Reminders}}", [T["on"], T["off"]]) as mr:
                with mr.case(T["on"]):
                    sc.set_value("Env", "reminders", "on")
                    save(T["on"])
                with mr.case(T["off"]):
                    sc.set_value("Env", "reminders", "off")
                    save(T["off"])
        with m.case(T["times"]):
            slot_ids: dict[str, str] = {}
            for u in users:
                for s in cfg["users"][u]["slots"]:
                    slot_ids.setdefault(s["id"], s["label"])
            labels = [f"{lab} ({sid})" for sid, lab in slot_ids.items()]
            with sc.menu(T["which"], labels) as mt:
                for (sid, lab), title in zip(slot_ids.items(), labels):
                    with mt.case(title):
                        cur = sc.get_value("{{Env}}", f"time_{sid}", split_path=False)
                        default = next(s["time"] for u in users for s in cfg["users"][u]["slots"] if s["id"] == sid)
                        with sc.if_(cur, "has any value") as b:
                            sc.set_var("CurTime", cur)
                            b.otherwise()
                            sc.set_var("CurTime", default)
                        new = sc.ask(f"{lab} {T['time_q']}", default="{{CurTime}}")
                        sc.set_value("Env", f"time_{sid}", new)
                        save(f"{lab} {new}")
        with m.case(T["show"]):
            sc.show("{{Env}}")
        with m.case(T["wipe"]):
            with sc.menu(T["wipe_q"], [T["wipe_yes"], T["cancel"]]) as mw:
                with mw.case(T["wipe_yes"]):
                    for k in ("today", "date", "history"):
                        sc.storage_wipe(k)
                    sc.notify(T["wiped"], "")


def _record(sc: Shortcut, cfg: dict, T: dict, u: str, word: str, all_types: list[str]) -> None:
    user = cfg["users"][u]
    slots = sorted(user["slots"], key=lambda s: len(s["label"]), reverse=True)

    # which slot? match "<label> ·" (longest label first)
    def choose(i: int):
        s = slots[i]
        if i == len(slots) - 1:
            _record_slot(sc, cfg, T, u, s, word, all_types)
            return
        with sc.if_("{{Picked}}", "contains", f"{s['label']} ·") as br:
            _record_slot(sc, cfg, T, u, s, word, all_types)
            br.otherwise()
            choose(i + 1)
    choose(0)


def _record_slot(sc: Shortcut, cfg: dict, T: dict, u: str, s: dict, word: str, all_types: list[str]) -> None:
    uemoji = cfg["users"][u]["emoji"]
    sid = s["id"]
    with sc.if_("{{Log}}", "contains", f"[{sid}]"):
        with sc.menu(T["again"], [T["again_yes"], T["cancel"]]) as m:
            with m.case(T["cancel"]):
                sc.exit()
    if s["nutrients"]:
        nut = sc.get_value("{{Plan}}", "{{User}}", split_path=False)
        nut = sc.get_value(nut, sid, split_path=False)
        nut = sc.get_value(nut, "nutrients", split_path=False)
        sc.health_log_from_dict(nut, sorted(s["nutrients"]))
    now = sc.format_date("HH:mm")
    sc.set_var("Log", f"{{{{Log}}}}[{sid}] {now} / ")
    sc.storage_set("today", "{{Log}}")
    sc.storage_set("date", "{{Today}}")

    # history: append, trim (a leading blank line shifts counts), keep last N
    old = sc.storage_get("history")
    entry = f"{{{{Today}}}} {now} {u} {s['label']}"
    with sc.if_(old, "has any value") as br:
        sc.set_var("Hist", f"{old}\n{entry}")
        br.otherwise()
        sc.set_var("Hist", entry)
    lines = sc.split_text(sc.trim("{{Hist}}"))
    n = sc.count(lines)
    with sc.if_(n, ">", HISTORY_MAX) as br:
        start = sc.math(n, "-", str(HISTORY_MAX - 1))
        rng = sc.item_from_list(lines, "Items in Range", start=start, end=n)
        sc.storage_set("history", sc.combine_text(rng))
        br.otherwise()
        sc.storage_set("history", sc.combine_text(lines))

    # reminders: complete today's for this slot, create tomorrow's for every slot if missing
    with sc.if_("{{Reminders}}", "is", "on"):
        today_found = sc.reminders_find(title_contains=f"{u} {s['label']} {word} {{{{TodayShort}}}}", completed=False)
        sc.reminders_complete(today_found)
        for t in cfg["users"][u]["slots"]:
            t_time = sc.get_value("{{Env}}", f"time_{t['id']}", split_path=False)
            with sc.if_(t_time, "has any value") as b:
                sc.set_var("AlertTime", t_time)
                b.otherwise()
                sc.set_var("AlertTime", t["time"])
            phrase = f"{u} {t['label']} {word} {{{{TomorrowShort}}}}"
            notes = "\n".join("💊 " + x for x in t["items"]) + (f"\n📝 {t['note']}" if t["note"] else "")
            sc.reminder_add_if_missing(f"{uemoji}{t['emoji']} {phrase} 💊{uemoji}", phrase,
                                       notes=notes, alert_at="{{Tomorrow}} {{AlertTime}}")
    sc.notify(f"{uemoji}{s['emoji']} {s['label']} {T['logged']}", f"{T['today']}: {{{{Log}}}}\n{s['note']}")


EXAMPLE_CONFIG: dict[str, Any] = {
    "name": "Supplement Check",
    "lang": "en",
    "word": "supplements",
    "users": {
        "Alex": {"emoji": "🩵", "slots": [
            {"id": "morning", "label": "Morning", "emoji": "🌅", "time": "08:00", "window": [0, 11],
             "items": ["Probiotic 1 capsule"], "nutrients": {}, "note": "after breakfast"},
            {"id": "lunch", "label": "Lunch", "emoji": "🍱", "time": "12:30", "window": [11, 16],
             "items": ["Vitamin D 2000 IU", "Multivitamin 1 tablet", "Omega-3 1 capsule"],
             "nutrients": {"Vitamin D": 50, "Vitamin C": 100, "Vitamin B12": 12, "Folate": 400, "Zinc": 8},
             "note": "with a meal that has some fat"},
            {"id": "bed", "label": "Bedtime", "emoji": "🌙", "time": "22:30", "window": [20, 24],
             "items": ["Magnesium 1 tablet"], "nutrients": {"Magnesium": 200}, "note": "30-60 min before sleep"},
        ]},
        "Sam": {"emoji": "💛", "slots": [
            {"id": "morning", "label": "Morning", "emoji": "🌅", "time": "07:30", "window": [0, 11],
             "items": ["Inositol 1 sachet", "Probiotic 1 capsule"], "nutrients": {"Folate": 400},
             "note": "empty stomach after waking"},
            {"id": "dinner", "label": "Dinner", "emoji": "🌆", "time": "18:30", "window": [16, 20],
             "items": ["Iron 25 mg"], "nutrients": {"Iron": 25}, "note": "keep 2h away from magnesium"},
        ]},
    },
}
