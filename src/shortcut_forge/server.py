"""MCP server: lets Claude (or any MCP client) design, lint, inspect and sign Apple Shortcuts.

Run:  shortcut-forge-mcp          (stdio)
      shortcut-forge-mcp --http   (streamable HTTP, for remote connectors)
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from importlib import resources
from typing import Any

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore

from . import __version__, health, sign as signing, templates
from .inspect import outline_file
from .lint import RULES, lint_file, summarize
from .spec import SpecError, build_from_spec, spec_reference

INSTRUCTIONS = """\
shortcut-forge builds real Apple Shortcuts (.shortcut files) for iPhone/iPad/Mac (iOS 27 aware).

Workflow:
1. Read the spec reference (tool `shortcut_reference` topic="spec") and pitfalls (topic="pitfalls") once.
2. Call `shortcut_build` with a JSON spec. It always lints; fix every error it reports and rebuild.
3. On macOS set sign=true to get a file the iPhone can import (AirDrop / iCloud Drive). Elsewhere, tell the
   user to sign on a Mac: `shortcuts sign -m anyone -i in.shortcut -o out.shortcut`.
4. For common needs use `shortcut_from_template` (supplement-tracker, water-log).
Ask the user before writing to Health or Reminders on their behalf only if the request is ambiguous.
Never claim a shortcut was tested on a device unless the user confirms it ran.
"""

mcp = _Server("shortcut-forge", instructions=INSTRUCTIONS)


def _out_dir() -> str:
    d = os.environ.get("SHORTCUT_FORGE_OUT") or os.path.join(os.path.expanduser("~"), "Downloads", "shortcut-forge")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except OSError:
        d = os.path.join(tempfile.gettempdir(), "shortcut-forge")
        os.makedirs(d, exist_ok=True)
        return d


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip() or "Shortcut"


def _finish(sc, output_path: str | None, sign: bool, sign_mode: str) -> dict[str, Any]:
    path = output_path or os.path.join(_out_dir(), _safe_name(sc.name) + ".unsigned.shortcut")
    sc.save(path)
    report = summarize(lint_file(path))
    result: dict[str, Any] = {"unsigned_path": path, "actions": len(sc.actions), "lint": report}
    if sign:
        if report["errors"]:
            result["signed"] = False
            result["sign_skipped"] = "lint errors must be fixed first"
        elif signing.can_sign():
            signed = os.path.join(os.path.dirname(path), _safe_name(sc.name) + ".shortcut")
            result["signed_path"] = signing.sign(path, signed, sign_mode)
            result["signed"] = True
        else:
            result["signed"] = False
            result["sign_hint"] = ("Not on macOS. Copy the file to a Mac and run: "
                                   f"shortcuts sign -m {sign_mode} -i in.shortcut -o out.shortcut")
    return result


@mcp.tool()
def shortcut_build(spec: dict, output_path: str | None = None, sign: bool = False,
                   sign_mode: str = "anyone") -> dict:
    """Build a .shortcut from a JSON spec ({"name": ..., "actions": [...]}) and lint it.

    See shortcut_reference(topic="spec") for every step type. Set sign=true on macOS to produce an
    importable signed file. Returns paths, action count and lint findings (fix all errors)."""
    try:
        sc = build_from_spec(spec)
    except SpecError as e:
        return {"error": str(e), "hint": "Call shortcut_reference(topic='spec') for step syntax."}
    return _finish(sc, output_path, sign, sign_mode)


@mcp.tool()
def shortcut_from_template(template: str, config: dict | None = None, output_path: str | None = None,
                           sign: bool = False, sign_mode: str = "anyone") -> dict:
    """Generate a shortcut from a ready-made template.

    template: "supplement-tracker" (multi-user supplements -> Apple Health + self-maintaining reminders,
    7-day Apple Intelligence report) or "water-log". config: template config; omit to get the example.
    Call shortcut_reference(topic="templates") to see each template's config shape."""
    try:
        mod = templates.get(template)
        sc = mod.build(config or mod.EXAMPLE_CONFIG)
    except ValueError as e:
        return {"error": str(e)}
    return _finish(sc, output_path, sign, sign_mode)


@mcp.tool()
def shortcut_lint(path: str) -> dict:
    """Lint an unsigned .shortcut file against known on-device failure patterns (rules SF000-SF013)."""
    try:
        return summarize(lint_file(path))
    except (OSError, ValueError) as e:
        return {"error": str(e)}


@mcp.tool()
def shortcut_inspect(path: str) -> str:
    """Return an indented, human-readable outline of an unsigned .shortcut file."""
    try:
        return outline_file(path)
    except (OSError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def shortcut_sign(path: str, output_path: str | None = None, mode: str = "anyone") -> dict:
    """Sign a .shortcut with the macOS `shortcuts` CLI so iOS can import it. mode: anyone | people-who-know-me."""
    try:
        return {"signed_path": signing.sign(path, output_path, mode), "signed": True}
    except (signing.SigningUnavailable, RuntimeError, ValueError, OSError) as e:
        return {"signed": False, "error": str(e)}


@mcp.tool()
def shortcut_reference(topic: str = "spec") -> str:
    """Docs for building shortcuts. topic: spec | pitfalls | lint-rules | health-types | templates | ios27."""
    topic = topic.lower()
    if topic == "spec":
        return spec_reference()
    if topic == "pitfalls":
        return _data("PITFALLS.md")
    if topic in ("lint", "lint-rules", "rules"):
        return "\n".join(f"{k} [{v[0]}] {v[1]} — symptom: {v[2]}" for k, v in RULES.items())
    if topic in ("health", "health-types"):
        return "\n".join(f"{t}: {u}" for t, u in sorted(health.ALL_TYPES.items())) + \
            "\n\nMicro-gram (mcg) values are converted to mg automatically."
    if topic == "templates":
        return "\n\n".join(f"## {n}\n{(m.__doc__ or '').strip()}\n\nExample config:\n"
                           f"{json.dumps(m.EXAMPLE_CONFIG, ensure_ascii=False, indent=1)}"
                           for n, m in templates.TEMPLATES.items())
    if topic in ("ios27", "ios"):
        return _data("IOS27.md")
    return "unknown topic; use spec | pitfalls | lint-rules | health-types | templates | ios27"


@mcp.resource("shortcut-forge://pitfalls")
def pitfalls_resource() -> str:
    """Field notes: what breaks shortcuts on real devices and how to avoid it."""
    return _data("PITFALLS.md")


@mcp.resource("shortcut-forge://spec")
def spec_resource() -> str:
    """JSON spec reference for shortcut_build."""
    return spec_reference()


@mcp.prompt()
def design_shortcut(goal: str) -> str:
    """Start designing a shortcut for a goal."""
    return (f"Design an Apple Shortcut for this goal: {goal}\n"
            "First read shortcut_reference('spec') and shortcut_reference('pitfalls'). Propose the flow in "
            "3-6 bullets, then call shortcut_build, fix lint errors, and sign it if on macOS.")


def _data(name: str) -> str:
    return resources.files("shortcut_forge").joinpath("data", name).read_text(encoding="utf-8")


def main() -> None:
    if "--version" in sys.argv:
        print(__version__)
        return
    if "--http" in sys.argv:
        mcp.run("streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
