"""Variable references and WF token serialization.

Every value that flows between Shortcuts actions is either
- a *token string* (text with embedded variables, ``WFTextTokenString``), or
- a *token attachment* (exactly one variable, ``WFTextTokenAttachment``).

Picking the wrong one is the #1 cause of shortcuts that import fine but
silently do nothing (see docs/PITFALLS.md, SF001 / SF004).
"""
from __future__ import annotations

import itertools
import re
import uuid
from dataclasses import dataclass
from typing import Any, Union

OBJ = "￼"  # object replacement char used as the placeholder inside token strings


def new_uuid() -> str:
    return str(uuid.uuid4()).upper()


def _u16(s: str) -> int:
    """Shortcuts counts attachment offsets in UTF-16 code units (emoji = 2)."""
    return len(s.encode("utf-16-le")) // 2


_registry: dict[int, "Ref"] = {}
_counter = itertools.count(1)
_MARK = re.compile(r"\x00ref:(\d+)\x00")
_NAMED = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

_SPECIAL = {
    "CurrentDate": {"Type": "CurrentDate"},
    "RepeatItem": {"Type": "Variable", "VariableName": "Repeat Item"},
    "RepeatIndex": {"Type": "Variable", "VariableName": "Repeat Index"},
    "ShortcutInput": {"Type": "ExtensionInput"},
    "Clipboard": {"Type": "Clipboard"},
    "Ask": {"Type": "Ask"},
    "DeviceDetails": {"Type": "DeviceDetails"},
}


@dataclass(frozen=True)
class Ref:
    """A reference to a value: a named variable, an action output, or a special variable."""

    data: tuple  # frozen representation of the underlying dict

    @classmethod
    def of(cls, d: dict) -> "Ref":
        return cls(tuple(sorted(d.items())))

    @property
    def dict(self) -> dict:
        return dict(self.data)

    # f-string support: f"Hello {name_ref}" embeds the variable in a token string
    def __format__(self, spec: str) -> str:
        n = next(_counter)
        _registry[n] = self
        return f"\x00ref:{n}\x00"

    __str__ = lambda self: self.__format__("")  # noqa: E731

    @property
    def kind(self) -> str:
        return self.dict.get("Type", "")

    @property
    def output_uuid(self) -> str | None:
        return self.dict.get("OutputUUID")

    @property
    def output_name(self) -> str | None:
        return self.dict.get("OutputName")

    @property
    def variable_name(self) -> str | None:
        return self.dict.get("VariableName")


def var(name: str) -> Ref:
    """Reference a named variable (or a special one: CurrentDate, RepeatItem, ShortcutInput, Clipboard)."""
    if name in _SPECIAL:
        return Ref.of(_SPECIAL[name])
    return Ref.of({"Type": "Variable", "VariableName": name})


def output(action_uuid: str, output_name: str) -> Ref:
    return Ref.of({"Type": "ActionOutput", "OutputUUID": action_uuid, "OutputName": output_name})


CURRENT_DATE = var("CurrentDate")
REPEAT_ITEM = var("RepeatItem")
SHORTCUT_INPUT = var("ShortcutInput")

Value = Union[str, int, float, Ref, None]


def split_parts(value: Value) -> list[Union[str, Ref]]:
    """Split a string containing f-string markers and/or {{Name}} templates into text and Ref parts."""
    if value is None:
        return [""]
    if isinstance(value, Ref):
        return [value]
    s = str(value)
    parts: list[Union[str, Ref]] = []
    pos = 0
    combined = re.compile(_MARK.pattern + "|" + _NAMED.pattern)
    for m in combined.finditer(s):
        if m.start() > pos:
            parts.append(s[pos:m.start()])
        if m.group(1):
            parts.append(_registry[int(m.group(1))])
        else:
            parts.append(var(m.group(2)))
        pos = m.end()
    if pos < len(s):
        parts.append(s[pos:])
    return parts or [""]


def single_ref(value: Value) -> Ref | None:
    """Return the Ref if the value is exactly one variable with no surrounding text."""
    parts = split_parts(value)
    if len(parts) == 1 and isinstance(parts[0], Ref):
        return parts[0]
    return None


def tok(value: Value) -> dict:
    """Serialize to a WFTextTokenString (text with embedded variables)."""
    s, att = "", {}
    for p in split_parts(value):
        if isinstance(p, str):
            s += p
        else:
            att["{%d, 1}" % _u16(s)] = p.dict
            s += OBJ
    return {"Value": {"string": s, "attachmentsByRange": att}, "WFSerializationType": "WFTextTokenString"}


def attach(ref: Ref) -> dict:
    """Serialize a single variable as WFTextTokenAttachment."""
    return {"Value": ref.dict, "WFSerializationType": "WFTextTokenAttachment"}


def cond_input(ref: Ref) -> dict:
    """The odd wrapper the `conditional` action expects for its WFInput."""
    return {"Type": "Variable", "Variable": attach(ref)}


def plain(value: Any) -> Any:
    """Turn a serialized parameter back into something human-readable (for inspect)."""
    if isinstance(value, dict):
        st = value.get("WFSerializationType")
        if st == "WFTextTokenString":
            v = value["Value"]
            s = v.get("string", "")
            out, last = "", 0
            atts = sorted(((int(k.strip("{}").split(",")[0]), a) for k, a in v.get("attachmentsByRange", {}).items()))
            u16 = s.encode("utf-16-le")
            for off, a in atts:
                out += u16[last * 2:off * 2].decode("utf-16-le") + "{" + describe_ref(a) + "}"
                last = off + 1
            out += u16[last * 2:].decode("utf-16-le")
            return out
        if st == "WFTextTokenAttachment":
            return "{" + describe_ref(value["Value"]) + "}"
        if value.get("Type") == "Variable" and "Variable" in value:
            return plain(value["Variable"])
        if "Type" in value:
            return "{" + describe_ref(value) + "}"
    return value


def describe_ref(d: dict) -> str:
    t = d.get("Type")
    if t == "Variable":
        return d.get("VariableName", "?")
    if t == "ActionOutput":
        return f"{d.get('OutputName', '?')}@{d.get('OutputUUID', '')[:4]}"
    return t or "?"
