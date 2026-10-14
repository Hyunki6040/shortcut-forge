"""Declarative JSON spec -> Shortcut. This is what the MCP tools accept from an LLM.

A spec is ``{"name": ..., "actions": [step, ...]}``. Each step is an object whose
first known key is the step type. Text fields accept ``{{Variable}}`` templates;
``"as": "name"`` stores the step's result in a named variable.

Special variables: {{CurrentDate}} {{RepeatItem}} {{RepeatIndex}} {{ShortcutInput}} {{Clipboard}}
"""
from __future__ import annotations

from typing import Any, Callable

from .builder import Shortcut

STEP_DOCS: dict[str, str] = {
    "comment": '{"comment": "note shown in the editor"}',
    "text": '{"text": "Hello {{name}}", "as": "greeting"}',
    "number": '{"number": "42", "as": "n"}',
    "set": '{"set": "varName", "to": "value or {{other}}"}',
    "append": '{"append": "listVar", "value": "item"}',
    "ask": '{"ask": "Your name?", "kind": "Text|Number|Date|URL", "default": "", "as": "name"}',
    "choose": '{"choose": "{{listVar}}", "prompt": "Pick one", "multiple": false, "as": "picked"}',
    "llm": '{"llm": "Summarize {{x}}", "model": "Apple Intelligence", "as": "summary"}  (iOS 26+)',
    "notify": '{"notify": "Title", "body": "Body {{x}}"}',
    "show": '{"show": "Result: {{x}}"}',
    "exit": '{"exit": true}',
    "open_url": '{"open_url": "https://example.com"}',
    "if": '{"if": ["{{x}}", "contains", "abc"], "then": [...], "else": [...]}  ops: is, is not, contains, '
          'does not contain, begins with, ends with, <, <=, >, >=, has any value, does not have any value',
    "menu": '{"menu": "Prompt", "cases": {"Option A": [...], "Option B": [...]}}',
    "repeat_each": '{"repeat_each": "{{listVar}}", "do": [... use {{RepeatItem}} ...]}',
    "repeat": '{"repeat": 3, "do": [...]}',
    "dict": '{"dict": {"a": {"b": 1}}, "as": "db"}',
    "get": '{"get": "{{db}}", "key": "a.b", "as": "v"}  (dotted keys are fetched level by level)',
    "set_key": '{"set_key": "dbVar", "key": "k", "value": "v"}',
    "date": '{"date": "yyyy-MM-dd", "offset_days": 1, "as": "tomorrow"}',
    "math": '{"math": ["{{a}}", "+", "1"], "as": "b"}  ops: + - × ÷ (or * /)',
    "count": '{"count": "{{listVar}}", "as": "n"}',
    "split": '{"split": "{{text}}", "separator": "New Lines", "as": "lines"}',
    "combine": '{"combine": "{{listVar}}", "separator": ", ", "as": "joined"}',
    "trim": '{"trim": "{{text}}", "as": "clean"}',
    "item": '{"item": "{{listVar}}", "which": "First Item|Last Item|Random Item|Item At Index", "index": 2, "as": "x"}',
    "storage_get": '{"storage_get": "key", "as": "v"}  (iOS 27 Stored Content)',
    "storage_set": '{"storage_set": "key", "value": "{{v}}"}',
    "storage_delete": '{"storage_delete": "key"}  (guarded: no error when missing)',
    "storage_wipe": '{"storage_wipe": "key"}  (overwrite+delete without reading; fixes corrupt values)',
    "health_log": '{"health_log": "Vitamin C", "value": "{{v}}", "unit": "mg"}  (mcg auto-converted)',
    "health_log_dict": '{"health_log_dict": "{{nutrients}}", "types": ["Vitamin C", "Vitamin D"]}',
    "reminders_find": '{"reminders_find": "phrase in title", "completed": false, "as": "found"}',
    "reminder_add": '{"reminder_add": "Title", "notes": "", "alert_at": "{{tomorrow}} 08:00", "if_missing": "phrase"}',
    "reminders_complete": '{"reminders_complete": "{{found}}"}',
    "run_shortcut": '{"run_shortcut": "Other Shortcut", "input": "{{x}}", "as": "result"}',
}


class SpecError(ValueError):
    pass


def build_from_spec(spec: dict) -> Shortcut:
    if not isinstance(spec, dict) or "actions" not in spec:
        raise SpecError('spec must be an object with "actions": [...]')
    sc = Shortcut(spec.get("name", "Shortcut"), color=spec.get("color", "blue"), glyph=spec.get("glyph", 59511),
                  storage_prefix=spec.get("storage_prefix", ""))
    _run(sc, spec["actions"], "actions")
    return sc


def _run(sc: Shortcut, steps: list, path: str) -> None:
    if not isinstance(steps, list):
        raise SpecError(f"{path} must be a list of steps")
    for i, step in enumerate(steps):
        where = f"{path}[{i}]"
        if not isinstance(step, dict):
            raise SpecError(f"{where} must be an object")
        kind = next((k for k in step if k in HANDLERS), None)
        if kind is None:
            raise SpecError(f"{where}: unknown step {list(step)}. Known: {', '.join(HANDLERS)}")
        try:
            result = HANDLERS[kind](sc, step, where)
        except SpecError:
            raise
        except (KeyError, TypeError, ValueError) as e:
            raise SpecError(f"{where} ({kind}): {e}. Example: {STEP_DOCS.get(kind, '')}") from e
        if step.get("as"):
            if result is None:
                raise SpecError(f"{where}: step {kind!r} has no result to store in 'as'")
            sc.set_var(step["as"], result)


def _if(sc: Shortcut, s: dict, where: str):
    cond = s["if"]
    if not isinstance(cond, list) or len(cond) not in (2, 3):
        raise SpecError(f'{where}: "if" must be [left, op] or [left, op, right]')
    left, op, right = (cond + [None])[:3]
    with sc.if_(left, op, right) as br:
        _run(sc, s.get("then", []), where + ".then")
        if "else" in s:
            br.otherwise()
            _run(sc, s["else"], where + ".else")


def _menu(sc: Shortcut, s: dict, where: str):
    cases = s["cases"]
    with sc.menu(s["menu"], list(cases)) as m:
        for title, body in cases.items():
            with m.case(title):
                _run(sc, body, f"{where}.cases[{title!r}]")


def _repeat_each(sc: Shortcut, s: dict, where: str):
    with sc.repeat_each(s["repeat_each"]):
        _run(sc, s.get("do", []), where + ".do")


def _repeat(sc: Shortcut, s: dict, where: str):
    with sc.repeat(int(s["repeat"])):
        _run(sc, s.get("do", []), where + ".do")


def _date(sc: Shortcut, s: dict, where: str):
    d = None
    if s.get("offset_days"):
        d = sc.adjust_date(s["offset_days"], "days", s.get("from"))
    elif s.get("from"):
        d = s["from"]
    return sc.format_date(s["date"], d)


def _reminder_add(sc: Shortcut, s: dict, where: str):
    kw = {k: s[k] for k in ("notes", "alert_at", "list_name") if k in s}
    if s.get("if_missing"):
        sc.reminder_add_if_missing(s["reminder_add"], s["if_missing"], **kw)
        return None
    return sc.reminder_add(s["reminder_add"], **kw)


HANDLERS: dict[str, Callable[[Shortcut, dict, str], Any]] = {
    "comment": lambda sc, s, w: sc.comment(s["comment"]),
    "text": lambda sc, s, w: sc.text(s["text"]),
    "number": lambda sc, s, w: sc.number(s["number"]),
    "set": lambda sc, s, w: sc.set_var(s["set"], s.get("to", "")),
    "append": lambda sc, s, w: sc.append_var(s["append"], s["value"]),
    "ask": lambda sc, s, w: sc.ask(s["ask"], kind=s.get("kind", "Text"), default=s.get("default")),
    "choose": lambda sc, s, w: sc.choose_from_list(s["choose"], s.get("prompt", ""), multiple=s.get("multiple", False)),
    "llm": lambda sc, s, w: sc.ask_llm(s["llm"], model=s.get("model", "Apple Intelligence")),
    "notify": lambda sc, s, w: sc.notify(s["notify"], s.get("body", "")),
    "show": lambda sc, s, w: sc.show(s["show"]),
    "exit": lambda sc, s, w: sc.exit(),
    "open_url": lambda sc, s, w: sc.open_url(s["open_url"]),
    "if": _if,
    "menu": _menu,
    "repeat_each": _repeat_each,
    "repeat": _repeat,
    "dict": lambda sc, s, w: sc.dictionary(s["dict"]),
    "get": lambda sc, s, w: sc.get_value(s["get"], s["key"]),
    "set_key": lambda sc, s, w: sc.set_value(s["set_key"], s["key"], s["value"]),
    "date": _date,
    "math": lambda sc, s, w: sc.math(*s["math"]),
    "count": lambda sc, s, w: sc.count(s["count"]),
    "split": lambda sc, s, w: sc.split_text(s["split"], s.get("separator", "New Lines")),
    "combine": lambda sc, s, w: sc.combine_text(s["combine"], s.get("separator", "New Lines")),
    "trim": lambda sc, s, w: sc.trim(s["trim"]),
    "item": lambda sc, s, w: sc.item_from_list(s["item"], s.get("which", "First Item"), index=s.get("index")),
    "storage_get": lambda sc, s, w: sc.storage_get(s["storage_get"]),
    "storage_set": lambda sc, s, w: sc.storage_set(s["storage_set"], s.get("value", "")),
    "storage_delete": lambda sc, s, w: sc.storage_delete(s["storage_delete"]),
    "storage_wipe": lambda sc, s, w: sc.storage_wipe(s["storage_wipe"]),
    "health_log": lambda sc, s, w: sc.health_log(s["health_log"], s["value"], s.get("unit")),
    "health_log_dict": lambda sc, s, w: sc.health_log_from_dict(s["health_log_dict"], s["types"], s.get("units")),
    "reminders_find": lambda sc, s, w: sc.reminders_find(title_contains=s["reminders_find"], completed=s.get("completed")),
    "reminder_add": _reminder_add,
    "reminders_complete": lambda sc, s, w: sc.reminders_complete(s["reminders_complete"]),
    "run_shortcut": lambda sc, s, w: sc.run_shortcut(s["run_shortcut"], s.get("input")),
}


def spec_reference() -> str:
    head = __doc__.strip() + "\n\nSteps:\n"
    return head + "\n".join(f"- {k}: {v}" for k, v in STEP_DOCS.items())
