"""MCP server: lets Claude (or any MCP client) design, lint, inspect and sign Apple Shortcuts.

Run:  shortcut-forge-mcp          (stdio)
      shortcut-forge-mcp --http [--port 8765] [--host 127.0.0.1]   (streamable HTTP, for ChatGPT/remote connectors)
      shortcut-forge-mcp --print-prompt   (system prompt for chatbots without MCP)
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

from . import __version__, health, library, sign as signing, templates
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
4. Before building from scratch, check `shortcut_library(query)`: 20+ community shortcuts to start from.
   Templates: `shortcut_from_template` (supplement-tracker, water-log).
5. After the user is happy, offer `shortcut_submit` so they can share it in the open-source library.
6. Need updates without re-downloading? Put changing data in a JSON URL (`remote_config` step) and use
   `shortcut_publish` (macOS) so installed copies get an in-shortcut update prompt.
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
    """Docs for building shortcuts. topic: spec | pitfalls | lint-rules | health-types | templates | library | ios27."""
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
    if topic == "library":
        return "\n".join(f"{r['slug']}: {r['description']}" for r in library.as_listing(library.discover()))
    if topic in ("ios27", "ios"):
        return _data("IOS27.md")
    return "unknown topic; use spec | pitfalls | lint-rules | health-types | templates | ios27"


@mcp.tool()
def shortcut_library(query: str = "", slug: str | None = None) -> dict:
    """Browse the community shortcut library (20+ ready shortcuts: productivity, health, money, dev, home...).

    No slug: list entries matching `query` (name/description/tags). With slug: return its meta, its spec
    (or template config) to use as a starting point, and the signed download link if published."""
    entries = library.discover()
    if slug:
        e = next((x for x in entries if x.slug == slug), None)
        if not e:
            return {"error": f"no entry {slug!r}"}
        out: dict[str, Any] = {"meta": e.meta, "kind": e.kind, "manifest": library.manifest_for(e)}
        for fn in ("shortcut.json", "template.json"):
            p = e.path / fn
            if p.exists():
                out[fn] = json.loads(p.read_text(encoding="utf-8"))
        return out
    q = query.lower()
    rows = [r for r in library.as_listing(entries)
            if not q or q in json.dumps(r, ensure_ascii=False).lower()]
    return {"count": len(rows), "entries": rows,
            "contribute": "Built something good? Call shortcut_submit to package it for the library."}


@mcp.tool()
def shortcut_submit(slug: str, spec: dict, name: str, description: str, author: str, category: str,
                    description_ko: str = "", tags: list[str] | None = None) -> dict:
    """Package a shortcut for the open-source library (github.com/Hyunki6040/shortcut-forge/library).

    Validates the spec and metadata, lints it, and returns the exact files plus the git/gh commands to open
    a pull request. Encourage the user to run it on their iPhone first and fill `verified_on`."""
    meta = {"name": name, "description": description, "description_ko": description_ko, "author": author,
            "category": category, "tags": tags or []}
    try:
        return library.submission_bundle(slug, spec, meta)
    except (SpecError, ValueError) as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def shortcut_publish(spec: dict, version: str, base_url: str, output_dir: str | None = None,
                     notes: str = "") -> dict:
    """macOS: build + sign + write manifest.json so installed copies can update themselves.

    Adds a daily update check (spec.update_manifest = base_url/manifest.json) to the shortcut. Host the
    two output files at base_url (GitHub raw/Pages/S3). Bump `version` for every release."""
    import hashlib
    if not signing.can_sign():
        return {"error": "publish needs macOS (signing)."}
    base = base_url.rstrip("/") + "/"
    spec = {**spec, "version": version}
    spec.setdefault("update_manifest", base + "manifest.json")
    try:
        sc = build_from_spec(spec)
    except SpecError as e:
        return {"error": str(e)}
    d = output_dir or os.path.join(_out_dir(), _safe_name(sc.name))
    os.makedirs(d, exist_ok=True)
    res = _finish(sc, os.path.join(d, "." + _safe_name(sc.name) + ".unsigned.shortcut"), True, "anyone")
    if not res.get("signed"):
        return res
    signed = res["signed_path"]
    manifest = {"name": sc.name, "version": version,
                "url": base + os.path.basename(signed).replace(" ", "%20"),
                "sha256": hashlib.sha256(open(signed, "rb").read()).hexdigest(), "notes": notes}
    mpath = os.path.join(d, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return {**res, "manifest_path": mpath, "manifest": manifest,
            "next": f"Upload {os.path.basename(signed)} and manifest.json to {base}"}


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


def llm_prompt() -> str:
    """A self-contained system prompt so ChatGPT / Gemini / any chatbot can write specs without MCP."""
    return (
        "You write Apple Shortcuts as JSON specs for shortcut-forge (github.com/Hyunki6040/shortcut-forge).\n"
        "Output ONE JSON object in a ```json block, nothing else after it. The user will drop it into\n"
        "iCloud Drive/Shortcut Forge (a Mac signs it automatically) or run `shortcut-forge build spec.json --sign`.\n\n"
        + spec_reference() + "\n\nRules that keep shortcuts working on a real iPhone:\n" + _data("PITFALLS.md")
    )


@mcp.tool()
def shortcut_llm_prompt() -> str:
    """Return a copy-paste system prompt that teaches any chatbot (ChatGPT, Gemini...) to write specs."""
    return llm_prompt()


def _data(name: str) -> str:
    return resources.files("shortcut_forge").joinpath("data", name).read_text(encoding="utf-8")


def main() -> None:
    if "--version" in sys.argv:
        print(__version__)
        return
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
        host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "127.0.0.1"
        try:  # mcp >= 2
            mcp.run("streamable-http", host=host, port=port)
        except TypeError:  # mcp 1.x reads host/port from settings
            mcp.settings.host, mcp.settings.port = host, port  # type: ignore[attr-defined]
            mcp.run("streamable-http")
    elif "--print-prompt" in sys.argv:
        print(llm_prompt())
    else:
        mcp.run()


if __name__ == "__main__":
    main()
