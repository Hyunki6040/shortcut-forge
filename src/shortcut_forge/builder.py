"""A small Python DSL that emits Apple Shortcuts (.shortcut) property lists.

Design rule: every helper encodes a lesson learned on a real iPhone. The
helpers produce the *shape the Shortcuts app actually accepts*, not merely a
plist that imports. See docs/PITFALLS.md for the failure behind each rule.

    sc = Shortcut("Hello")
    name = sc.ask("Your name?")
    with sc.if_(name, "contains", "Claude") as br:
        sc.notify("Hi", f"Welcome back {name}")
        br.otherwise()
        sc.notify("Hi", f"Nice to meet you {name}")
    sc.save("hello.shortcut")
"""
from __future__ import annotations

import contextlib
import json
import plistlib
from typing import Any, Iterator

from . import health
from .refs import (CURRENT_DATE, REPEAT_ITEM, Ref, Value, attach, cond_input, new_uuid, output, single_ref,
                   split_parts, tok, var)

PREFIX = "is.workflow.actions."

# conditional operators -> (code, kind)   kind: text | number | unary
OPERATORS: dict[str, tuple[int, str]] = {
    "<": (0, "number"), "<=": (1, "number"), ">": (2, "number"), ">=": (3, "number"),
    "is": (4, "text"), "==": (4, "text"), "is not": (5, "text"), "!=": (5, "text"),
    "begins with": (8, "text"), "ends with": (9, "text"),
    "contains": (99, "text"), "does not contain": (999, "text"),
    "has any value": (100, "unary"), "has value": (100, "unary"),
    "does not have any value": (101, "unary"), "no value": (101, "unary"),
}

ICON_COLORS = {  # WFWorkflowIconStartColor values
    "red": 4282601983, "orange": 4251333119, "yellow": 4274264319, "green": 4292093695,
    "teal": 431817727, "lightblue": 1440408063, "blue": 463140863, "darkblue": 946986751,
    "purple": 2071128575, "pink": 3679049983, "gray": 255, "brown": 3031607807,
}


class Branch:
    """Handle returned by ``Shortcut.if_`` so the body can switch to the else-branch."""

    def __init__(self, sc: "Shortcut", group: str):
        self._sc, self._group, self.has_else = sc, group, False

    def otherwise(self) -> None:
        if self.has_else:
            raise RuntimeError("otherwise() called twice")
        self.has_else = True
        self._sc.add("conditional", GroupingIdentifier=self._group, WFControlFlowMode=1)


class Menu:
    def __init__(self, sc: "Shortcut", group: str, items: list[str]):
        self._sc, self._group, self._items, self._seen = sc, group, items, []

    @contextlib.contextmanager
    def case(self, title: str) -> Iterator[None]:
        if title not in self._items:
            raise ValueError(f"menu case {title!r} not declared in items {self._items}")
        self._seen.append(title)
        self._sc.add("choosefrommenu", GroupingIdentifier=self._group, WFControlFlowMode=1, WFMenuItemTitle=title)
        yield


class Shortcut:
    """Accumulates actions and serializes them to a .shortcut plist."""

    def __init__(self, name: str = "Shortcut", *, color: str | int = "blue", glyph: int = 59511,
                 storage_prefix: str = "", input_classes: list[str] | None = None, version: str | None = None):
        self.name = name
        self.version = version
        self.actions: list[dict] = []
        self.color = ICON_COLORS.get(color, color) if isinstance(color, str) else color
        self.glyph = glyph
        self.storage_prefix = storage_prefix  # e.g. "qa_" to sandbox a test run
        self.input_classes = input_classes or ["WFStringContentItem"]
        self._depth = 0

    # ------------------------------------------------------------------ core
    def add(self, ident: str, uuid: str | None = None, **params: Any) -> str:
        if uuid:
            params["UUID"] = uuid
        full = ident if ident.startswith((PREFIX, "com.", "is.")) else PREFIX + ident
        self.actions.append({"WFWorkflowActionIdentifier": full, "WFWorkflowActionParameters": params})
        return params.get("UUID", "")

    def _out(self, ident: str, out_name: str, **params: Any) -> Ref:
        u = new_uuid()
        self.add(ident, u, **params)
        return output(u, out_name)

    def as_ref(self, value: Value) -> Ref:
        """Coerce text-with-variables into a single Ref (adds a Text action when needed)."""
        r = single_ref(value)
        return r if r is not None else self.text(value)

    # --------------------------------------------------------------- basics
    def comment(self, text: str) -> None:
        self.add("comment", WFCommentActionText=text)

    def text(self, value: Value) -> Ref:
        return self._out("gettext", "Text", WFTextActionText=tok(value))

    def number(self, value: Value) -> Ref:
        return self._out("number", "Number", WFNumberActionNumber=tok(value))

    def set_var(self, name: str, value: Value) -> Ref:
        self.add("setvariable", WFVariableName=name, WFInput=attach(self.as_ref(value)))
        return var(name)

    def append_var(self, name: str, value: Value) -> Ref:
        self.add("appendvariable", WFVariableName=name, WFInput=attach(self.as_ref(value)))
        return var(name)

    def show(self, value: Value) -> None:
        self.add("showresult", Text=tok(value))

    def notify(self, title: Value, body: Value = "") -> None:
        self.add("notification", WFNotificationActionTitle=tok(title), WFNotificationActionBody=tok(body))

    def exit(self) -> None:
        self.add("exit")

    def open_url(self, url: Value) -> None:
        self.add("openurl", WFInput=tok(url))

    def run_shortcut(self, name: str, input: Value = None) -> Ref:
        p: dict[str, Any] = {"WFWorkflow": {"workflowName": name, "isSelf": False}, "WFWorkflowName": name}
        if input is not None:
            p["WFInput"] = attach(self.as_ref(input))
        return self._out("runworkflow", "Shortcut Result", **p)

    # ---------------------------------------------------------------- input
    def ask(self, prompt: Value, *, kind: str = "Text", default: Value = None) -> Ref:
        p: dict[str, Any] = {"WFAskActionPrompt": tok(prompt), "WFInputType": kind}
        if default is not None:
            p["WFAskActionDefaultAnswer"] = tok(default)
        return self._out("ask", "Provided Input", **p)

    def choose_from_list(self, items: Value, prompt: Value = "", *, multiple: bool = False) -> Ref:
        p: dict[str, Any] = {"WFInput": attach(self.as_ref(items)), "WFChooseFromListActionPrompt": tok(prompt)}
        if multiple:
            p["WFChooseFromListActionSelectMultiple"] = True
        return self._out("choosefromlist", "Chosen Item", **p)

    def ask_llm(self, prompt: Value, *, model: str = "Apple Intelligence", result: str = "Text") -> Ref:
        """iOS 26+ "Use Model". model: "Apple Intelligence" (on-device / Private Cloud Compute) or "ChatGPT"."""
        return self._out("askllm", "Response", WFLLMPrompt=tok(prompt), WFLLMModel=model, WFGenerativeResultType=result)

    # ------------------------------------------------------------ text/list
    def split_text(self, text: Value, separator: str = "New Lines") -> Ref:
        p: dict[str, Any] = {"text": tok(text)}
        if separator in ("New Lines", "Spaces", "Every Character"):
            p["WFTextSeparator"] = separator
        else:
            p.update(WFTextSeparator="Custom", WFTextCustomSeparator=separator)
        return self._out("text.split", "Split Text", **p)

    def combine_text(self, items: Value, separator: str = "New Lines") -> Ref:
        p: dict[str, Any] = {"text": attach(self.as_ref(items))}
        if separator in ("New Lines", "Spaces"):
            p["WFTextSeparator"] = separator
        else:
            p.update(WFTextSeparator="Custom", WFTextCustomSeparator=separator)
        return self._out("text.combine", "Combined Text", **p)

    def trim(self, text: Value) -> Ref:
        """Trim whitespace. Do this before splitting stored history, or a leading blank line shifts every count."""
        return self._out("text.trimwhitespace", "Updated Text", WFInput=tok(text))

    def replace_text(self, text: Value, find: str, replace: str, *, regex: bool = False) -> Ref:
        return self._out("text.replace", "Updated Text", WFInput=tok(text), WFReplaceTextFind=find,
                         WFReplaceTextReplace=replace, WFReplaceTextRegularExpression=regex)

    def count(self, items: Value) -> Ref:
        return self._out("count", "Count", WFCountType="Items", Input=attach(self.as_ref(items)))

    def item_from_list(self, items: Value, which: str = "First Item", *, index: Value = None,
                       start: Value = None, end: Value = None) -> Ref:
        p: dict[str, Any] = {"WFInput": attach(self.as_ref(items)), "WFItemSpecifier": which}
        if which == "Item At Index":
            p["WFItemIndex"] = tok(index)
        if which == "Items in Range":
            p.update(WFItemRangeStart=tok(start), WFItemRangeEnd=tok(end))
            return self._out("getitemfromlist", "Items in Range", **p)
        return self._out("getitemfromlist", "Item from List", **p)

    def math(self, a: Value, op: str, b: Value) -> Ref:
        op = {"/": "÷", "*": "×"}.get(op, op)
        operand = tok(b) if any(isinstance(p, Ref) for p in split_parts(b)) else str(b)
        return self._out("math", "Calculation Result", WFInput=tok(a), WFMathOperation=op, WFMathOperand=operand)

    # ---------------------------------------------------------------- dates
    def format_date(self, fmt: str, date: Value = None) -> Ref:
        return self._out("format.date", "Formatted Date", WFDateFormatStyle="Custom", WFDateFormat=fmt,
                         WFDate=tok(date if date is not None else CURRENT_DATE))

    def adjust_date(self, amount: int | float, unit: str = "days", date: Value = None) -> Ref:
        op = "Add" if amount >= 0 else "Subtract"
        return self._out("adjustdate", "Adjusted Date", WFDate=tok(date if date is not None else CURRENT_DATE),
                         WFAdjustOperation=op,
                         WFDuration={"Value": {"Magnitude": str(abs(amount)), "Unit": unit},
                                     "WFSerializationType": "WFQuantityFieldValue"})

    # ---------------------------------------------------------- dictionaries
    def dictionary(self, data: dict | list) -> Ref:
        """Nested JSON -> Dictionary. Text + "Get Dictionary from Input" is the robust path for deep data."""
        t = self.text(json.dumps(data, ensure_ascii=False, indent=1))
        return self.to_dict(t)

    def to_dict(self, value: Value) -> Ref:
        return self._out("detect.dictionary", "Dictionary", WFInput=attach(self.as_ref(value)))

    def get_value(self, dictionary: Value, key: Value, *, split_path: bool = True) -> Ref:
        """Get a value. "a.b.c" is fetched one level at a time: a native key path throws
        ("cannot evaluate key path") as soon as a parent key is missing."""
        d = self.as_ref(dictionary)
        keys: list[Value]
        if split_path and isinstance(key, str) and "." in key and single_ref(key) is None and "\x00" not in key:
            keys = key.split(".")
        else:
            keys = [key]
        r = d
        for k in keys:
            r = self._out("getvalueforkey", "Dictionary Value", WFInput=attach(r),
                          WFGetDictionaryValueType="Value", WFDictionaryKey=tok(k))
        return r

    def set_value(self, var_name: str, key: Value, value: Value) -> Ref:
        """Set key on the dictionary held in variable ``var_name`` and store it back."""
        r = self._out("setvalueforkey", "Dictionary", WFDictionary=attach(var(var_name)),
                      WFDictionaryKey=tok(key), WFDictionaryValue=tok(value))
        return self.set_var(var_name, r)

    # ------------------------------------------------- iOS 27 stored content
    def _key(self, key: str) -> str:
        return self.storage_prefix + key

    def storage_get(self, key: str, *, global_scope: bool = False) -> Ref:
        return self._out("getstoredcontent", "Stored Content", WFStoredContentKey=self._key(key),
                         WFStoredContentGlobalValue=global_scope)

    def storage_set(self, key: str, value: Value, *, global_scope: bool = False) -> None:
        # MUST be a token string. An attachment imports fine and stores nothing.
        self.add("setstoredcontent", new_uuid(), WFInput=tok(value), WFStoredContentKey=self._key(key),
                 WFStoredContentGlobalValue=global_scope)

    def storage_delete(self, key: str, *, global_scope: bool = False, guarded: bool = True) -> None:
        """Deleting a key that does not exist raises error 16, so read first and delete only when present."""
        if guarded:
            cur = self.storage_get(key, global_scope=global_scope)
            with self.if_(cur, "has any value"):
                self.add("deletestoredcontent", WFStoredContentKey=self._key(key), WFStoredContentGlobalValue=global_scope)
        else:
            self.add("deletestoredcontent", WFStoredContentKey=self._key(key), WFStoredContentGlobalValue=global_scope)

    def storage_wipe(self, key: str, *, global_scope: bool = False) -> None:
        """Overwrite then delete without reading. Safe even when the stored value is corrupt
        (reading a corrupt value fails with "could not communicate with a helper application")."""
        self.storage_set(key, "-", global_scope=global_scope)
        self.storage_delete(key, global_scope=global_scope, guarded=False)

    # ----------------------------------------------------------------- health
    def health_log(self, sample_type: str, value: Value, unit: str | None = None, *, date: Value = None) -> None:
        """Log one quantity sample. ``sample_type`` must be a literal (a variable type is rejected on device).
        Micro-gram values are converted to mg because the unit string "mcg" is read as grams."""
        unit = unit or health.default_unit(sample_type)
        r = single_ref(value)
        if r is None:  # literal number or mixed text -> make it a real number first
            r = self.number(value)
        if health.is_micro(unit):
            r = self.math(r, "÷", "1000")
            unit = "mg"
        p: dict[str, Any] = {
            "WFQuantitySampleType": sample_type,
            # Magnitude MUST be the raw variable dict, not a token string ("choose a value for each parameter")
            "WFQuantitySampleQuantity": {"Value": {"Magnitude": r.dict, "Unit": unit},
                                         "WFSerializationType": "WFQuantityFieldValue"},
        }
        if date is not None:
            p["WFQuantitySampleDate"] = tok(date)
        self.add("health.quantity.log", new_uuid(), **p)

    def health_log_from_dict(self, dictionary: Value, types: list[str], units: dict[str, str] | None = None) -> None:
        """For each Health type, read ``dictionary[type]`` and log it only when present."""
        d = self.as_ref(dictionary)
        for t in types:
            v = self.get_value(d, t, split_path=False)
            with self.if_(v, "has any value"):
                self.health_log(t, v, (units or {}).get(t))

    # -------------------------------------------------------------- reminders
    def reminders_find(self, *, title_contains: Value = None, completed: bool | None = None,
                       limit: int | None = None) -> Ref:
        tmpl = []
        if title_contains is not None:
            tmpl.append({"Property": "Title", "Operator": 99, "Values": {"String": tok(title_contains), "Unit": 4},
                         "Removable": True, "VariableOverrides": {}})
        if completed is not None:
            tmpl.append({"Property": "Is Completed", "Operator": 4, "Values": {"Bool": completed, "Unit": 4},
                         "Removable": True, "VariableOverrides": {}})
        p: dict[str, Any] = {"WFContentItemFilter": {"Value": {
            "WFActionParameterFilterPrefix": 1, "WFContentPredicateBoundedDate": False,
            "WFActionParameterFilterTemplates": tmpl}, "WFSerializationType": "WFContentPredicateTableTemplate"},
            "WFContentItemLimitEnabled": limit is not None}
        if limit is not None:
            p["WFContentItemLimitNumber"] = limit
        return self._out("filter.reminders", "Reminders", **p)

    def reminder_add(self, title: Value, *, notes: Value = None, alert_at: Value = None, list_name: str | None = None) -> Ref:
        """alert_at: text like "2026-10-15 08:00" (date and time, as text)."""
        p: dict[str, Any] = {"WFCalendarItemTitle": tok(title)}
        if notes is not None:
            p["WFCalendarItemNotes"] = tok(notes)
        if alert_at is not None:
            p.update(WFAlertEnabled="Alert", WFAlertCondition="At Time", WFAlertCustomTime=tok(alert_at))
        if list_name:
            p["WFCalendarItemCalendar"] = list_name
        return self._out("addnewreminder", "New Reminder", **p)

    def reminders_complete(self, reminders: Value) -> None:
        """Mark found reminders done. Setting a property on a *list* pops an item picker, so loop;
        and skip entirely when nothing was found (an empty input is a "choose a value" error)."""
        r = self.as_ref(reminders)
        n = self.count(r)
        with self.if_(n, ">", 0):
            with self.repeat_each(r) as item:
                self.add("setters.reminders", WFInput=attach(item), WFContentItemPropertyName="Is Completed",
                         WFReminderContentItemIsCompleted=True)

    def reminder_add_if_missing(self, title: Value, search: Value, **kw: Any) -> None:
        """Idempotent create: search an open reminder by a fixed phrase, create only when none matches."""
        found = self.reminders_find(title_contains=search, completed=False)
        n = self.count(found)
        with self.if_(n, "<", 1):
            self.reminder_add(title, **kw)

    # ------------------------------------------------------ web / device
    def url(self, value: Value) -> Ref:
        return self._out("url", "URL", WFURLActionURL=tok(value))

    def get_url(self, url: Value, *, method: str = "GET", json_body: dict | None = None,
                headers: dict | None = None) -> Ref:
        """Get Contents of URL. A network error aborts the whole run (Shortcuts has no try/catch),
        so fetch at most once a day and cache in Stored Content (see remote_config)."""
        p: dict[str, Any] = {"WFURL": tok(url), "WFHTTPMethod": method}
        if headers:
            p["ShowHeaders"] = True
            p["WFHTTPHeaders"] = _dict_field(headers)
        if json_body is not None:
            p["WFHTTPBodyType"] = "JSON"
            p["WFJSONValues"] = _dict_field(json_body)
        return self._out("downloadurl", "Contents of URL", **p)

    def get_clipboard(self) -> Ref:
        return self._out("getclipboard", "Clipboard")

    def set_clipboard(self, value: Value) -> None:
        self.add("setclipboard", WFInput=attach(self.as_ref(value)))

    def speak(self, text: Value) -> None:
        self.add("speaktext", WFText=tok(text))

    def share(self, value: Value) -> None:
        self.add("share", WFInput=attach(self.as_ref(value)))

    def wait(self, seconds: float) -> None:
        self.add("delay", WFDelayTime=seconds)

    def vibrate(self) -> None:
        self.add("vibrate")

    def battery_level(self) -> Ref:
        return self._out("getbatterylevel", "Battery Level")

    def current_location(self) -> Ref:
        return self._out("getcurrentlocation", "Current Location")

    def weather(self) -> Ref:
        return self._out("weather.currentconditions", "Weather Conditions")

    def list_(self, items: list[str]) -> Ref:
        return self._out("list", "List", WFItems=[str(i) for i in items])

    def open_app(self, bundle_id: str, name: str | None = None) -> None:
        self.add("openapp", WFAppIdentifier=bundle_id,
                 WFSelectedApp={"BundleIdentifier": bundle_id, "Name": name or bundle_id})

    def calendar_add(self, title: Value, start: Value, end: Value, *, notes: Value = None,
                     calendar: str | None = None) -> Ref:
        p: dict[str, Any] = {"WFCalendarItemTitle": tok(title), "WFCalendarItemStartDate": tok(start),
                             "WFCalendarItemEndDate": tok(end)}
        if notes is not None:
            p["WFCalendarItemNotes"] = tok(notes)
        if calendar:
            p["WFCalendarItemCalendar"] = calendar
        return self._out("addnewevent", "New Event", **p)

    def raw(self, identifier: str, output: str | None = None, **params: Any) -> Ref | None:
        """Escape hatch for any action not wrapped yet. Values that are Ref become attachments,
        strings with {{vars}} become token strings; dicts/lists/numbers/bools pass through."""
        conv: dict[str, Any] = {}
        for k, v in params.items():
            if isinstance(v, Ref):
                conv[k] = attach(v)
            elif isinstance(v, str) and any(isinstance(x, Ref) for x in split_parts(v)):
                conv[k] = tok(v)
            else:
                conv[k] = v
        if output:
            return self._out(identifier, output, **conv)
        self.add(identifier, **conv)
        return None

    # ------------------------------------------------- remote data & updates
    def remote_config(self, url: Value, cache_key: str = "remote_config") -> Ref:
        """Fetch JSON at most once a day, cache it in Stored Content and return a Dictionary.
        Split code from data: change the JSON on the web and every installed copy picks it up
        tomorrow, no re-download. Returns the cached copy on other runs."""
        today = self.format_date("yyyy-MM-dd")
        with self.if_(self.storage_get(cache_key + "_date"), "is", today) as br:
            self.set_var("_RemoteRaw", self.storage_get(cache_key))
            br.otherwise()
            fetched = self.get_url(url)
            with self.if_(fetched, "has any value") as b2:
                self.storage_set(cache_key, fetched)
                self.storage_set(cache_key + "_date", today)
                self.set_var("_RemoteRaw", fetched)
                b2.otherwise()
                self.set_var("_RemoteRaw", self.storage_get(cache_key))
        return self.to_dict("{{_RemoteRaw}}")

    def update_check(self, version: str, manifest_url: Value, *, cache_key: str = "_update_checked",
                     prompt: str = "Update available") -> None:
        """Once a day, read a manifest {"version": "...", "url": "...", "notes": "..."} (written by
        `shortcut-forge publish`). If the version differs, offer to open the new signed file;
        iOS then asks to replace the installed shortcut."""
        today = self.format_date("yyyy-MM-dd")
        with self.if_(self.storage_get(cache_key), "is", today) as br:
            br.otherwise()
            self.storage_set(cache_key, today)
            m = self.to_dict(self.get_url(manifest_url))
            latest = self.get_value(m, "version", split_path=False)
            with self.if_(latest, "has any value"):
                with self.if_(latest, "is not", version):
                    notes = self.get_value(m, "notes", split_path=False)
                    with self.menu(f"{prompt}: {version} → {latest}\n{notes}", ["Update", "Later"]) as mu:
                        with mu.case("Update"):
                            self.open_url(self.get_value(m, "url", split_path=False))

    # ---------------------------------------------------------- control flow
    @contextlib.contextmanager
    def if_(self, left: Value, op: str, right: Value = None) -> Iterator[Branch]:
        """Conditional. Text comparisons first pass the left side through a Text action: a dictionary
        value or chosen item compared as text otherwise shows an empty field and fails on device."""
        if op not in OPERATORS:
            raise ValueError(f"unknown operator {op!r}; use one of {sorted(OPERATORS)}")
        code, kind = OPERATORS[op]
        lref = self.text(left) if kind == "text" else self.as_ref(left)
        g = new_uuid()
        p: dict[str, Any] = {"GroupingIdentifier": g, "WFControlFlowMode": 0, "WFCondition": code,
                             "WFInput": cond_input(lref)}
        if kind == "number":
            if isinstance(right, Ref) or (isinstance(right, str) and single_ref(right) is not None):
                raise ValueError("number comparisons need a literal right-hand side (Shortcuts limitation)")
            p["WFNumberValue"] = str(right)
        elif kind == "text":
            p["WFConditionalActionString"] = tok(right if right is not None else "")
        self.add("conditional", **p)
        br = Branch(self, g)
        yield br
        self.add("conditional", new_uuid(), GroupingIdentifier=g, WFControlFlowMode=2)

    @contextlib.contextmanager
    def menu(self, prompt: Value, items: list[str]) -> Iterator[Menu]:
        g = new_uuid()
        self.add("choosefrommenu", GroupingIdentifier=g, WFControlFlowMode=0, WFMenuPrompt=tok(prompt), WFMenuItems=list(items))
        m = Menu(self, g, list(items))
        yield m
        missing = [i for i in items if i not in m._seen]
        for title in missing:  # every declared item needs a branch, even an empty one
            self.add("choosefrommenu", GroupingIdentifier=g, WFControlFlowMode=1, WFMenuItemTitle=title)
        self.add("choosefrommenu", new_uuid(), GroupingIdentifier=g, WFControlFlowMode=2)

    @contextlib.contextmanager
    def repeat_each(self, items: Value) -> Iterator[Ref]:
        g = new_uuid()
        self.add("repeat.each", GroupingIdentifier=g, WFControlFlowMode=0, WFInput=attach(self.as_ref(items)))
        yield REPEAT_ITEM
        self.add("repeat.each", new_uuid(), GroupingIdentifier=g, WFControlFlowMode=2)

    @contextlib.contextmanager
    def repeat(self, times: int) -> Iterator[Ref]:
        g = new_uuid()
        self.add("repeat.count", GroupingIdentifier=g, WFControlFlowMode=0, WFRepeatCount=times)
        yield var("RepeatIndex")
        self.add("repeat.count", new_uuid(), GroupingIdentifier=g, WFControlFlowMode=2)

    # ------------------------------------------------------------- output
    def to_plist(self) -> dict:
        return {
            "WFWorkflowActions": self.actions,
            "WFWorkflowClientVersion": "5037.0.17",
            "WFWorkflowMinimumClientVersion": 900,
            "WFWorkflowMinimumClientVersionString": "900",
            "WFWorkflowIcon": {"WFWorkflowIconStartColor": self.color, "WFWorkflowIconGlyphNumber": self.glyph},
            "WFWorkflowImportQuestions": [],
            "WFWorkflowTypes": [],
            "WFWorkflowInputContentItemClasses": self.input_classes,
            "WFWorkflowHasShortcutInputVariables": False,
            "WFWorkflowHasOutputFallback": False,
            "WFWorkflowOutputContentItemClasses": [],
            "WFWorkflowName": self.name,
        }

    def to_bytes(self) -> bytes:
        return plistlib.dumps(self.to_plist(), fmt=plistlib.FMT_BINARY)

    def save(self, path: str) -> str:
        with open(path, "wb") as f:
            f.write(self.to_bytes())
        return path

    def lint(self):
        from .lint import lint_plist
        return lint_plist(self.to_plist())


def _dict_field(d: dict) -> dict:
    items = []
    for k, v in d.items():
        if isinstance(v, bool):
            items.append({"WFItemType": 4, "WFKey": tok(k), "WFValue": {"Value": v, "WFSerializationType": "WFNumberSubstitutableState"}})
        elif isinstance(v, (int, float)):
            items.append({"WFItemType": 3, "WFKey": tok(k), "WFValue": tok(str(v))})
        else:
            items.append({"WFItemType": 0, "WFKey": tok(k), "WFValue": tok(v)})
    return {"Value": {"WFDictionaryFieldValueItems": items}, "WFSerializationType": "WFDictionaryFieldValue"}


__all__ = ["Shortcut", "Branch", "Menu", "OPERATORS", "split_parts"]
