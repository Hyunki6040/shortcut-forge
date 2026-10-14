"""Human-readable outline of an unsigned .shortcut plist."""
from __future__ import annotations

import plistlib

from .refs import plain

_KEYS_OF_INTEREST = (
    "WFTextActionText", "WFVariableName", "WFInput", "WFCondition", "WFConditionalActionString", "WFNumberValue",
    "WFMenuPrompt", "WFMenuItems", "WFMenuItemTitle", "WFStoredContentKey", "WFQuantitySampleType",
    "WFQuantitySampleQuantity", "WFCalendarItemTitle", "WFAlertCustomTime", "WFDictionaryKey", "WFLLMPrompt",
    "WFNotificationActionTitle", "WFNotificationActionBody", "WFCommentActionText", "WFAskActionPrompt",
    "WFDateFormat", "WFMathOperation", "WFMathOperand",
)
_COND = {0: "<", 1: "<=", 2: ">", 3: ">=", 4: "is", 5: "is not", 8: "begins with", 9: "ends with",
         99: "contains", 999: "does not contain", 100: "has any value", 101: "has no value"}


def outline(plist: dict, max_len: int = 90) -> str:
    lines, depth = [], 0
    for i, a in enumerate(plist.get("WFWorkflowActions", [])):
        ident = a["WFWorkflowActionIdentifier"].replace("is.workflow.actions.", "")
        p = a.get("WFWorkflowActionParameters", {})
        mode = p.get("WFControlFlowMode")
        if mode in (1, 2):
            depth = max(depth - 1, 0)
        label = ident
        if mode == 1:
            label = "otherwise" if ident == "conditional" else f"case {p.get('WFMenuItemTitle', '')!r}"
        elif mode == 2:
            label = f"end {ident}"
        details = []
        if mode in (None, 0):
            for k in _KEYS_OF_INTEREST:
                if k in p:
                    v = p[k]
                    if k == "WFCondition":
                        v = _COND.get(v, v)
                    else:
                        v = plain(v)
                        if isinstance(v, dict) and "Value" in v:
                            v = {kk: plain(vv) for kk, vv in v["Value"].items()}
                    s = str(v).replace("\n", "⏎")
                    details.append(f"{k.replace('WF', '')}={s[:max_len]}")
        lines.append(f"{i:4d} " + "  " * depth + label + ("  " + " | ".join(details) if details else ""))
        if mode in (0, 1):
            depth += 1
    return "\n".join(lines)


def outline_file(path: str) -> str:
    with open(path, "rb") as f:
        if f.read(4) == b"AEA1":
            raise ValueError("Signed file (AEA1). Inspect the unsigned plist instead.")
        f.seek(0)
        return outline(plistlib.load(f))
