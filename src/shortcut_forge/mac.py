"""Mac automation: a folder watcher that turns specs and unsigned files into signed shortcuts.

    shortcut-forge mac watch                 # foreground
    shortcut-forge mac install-agent         # run it forever via launchd (login item)

Default inbox is iCloud Drive/Shortcut Forge, so you can drop a JSON spec from any device
(ChatGPT on the web, Codex, a teammate) and pick up the signed file on your iPhone in the Files app:

    iCloud Drive/Shortcut Forge/            <- drop *.json specs or *.unsigned.shortcut here
    iCloud Drive/Shortcut Forge/Signed/     <- signed *.shortcut appear here (tap on iPhone to add)
    iCloud Drive/Shortcut Forge/Failed/     <- inputs that failed, with a .log next to them
"""
from __future__ import annotations

import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import sign as signing
from .lint import lint_plist, summarize
from .spec import SpecError, build_from_spec

ICLOUD = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
DEFAULT_INBOX = ICLOUD / "Shortcut Forge" if ICLOUD.exists() else Path.home() / "Shortcut Forge"
LABEL = "io.github.hyunki6040.shortcut-forge"
AGENT = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def process_file(path: Path, signed_dir: Path, failed_dir: Path, *, mode: str = "anyone",
                 open_in_app: bool = False) -> Path | None:
    name = path.name
    try:
        if name.endswith(".json"):
            spec = json.loads(path.read_text(encoding="utf-8"))
            sc = build_from_spec(spec)
            data = sc.to_bytes()
            base = sc.name
        elif name.endswith(".shortcut"):
            data = path.read_bytes()
            if data[:4] == signing.SIGNED_MAGIC:
                return None  # already signed
            base = name.replace(".unsigned", "").removesuffix(".shortcut")
        else:
            return None
        rep = summarize(lint_plist(plistlib.loads(data)))
        if rep["errors"]:
            raise ValueError("lint errors: " + "; ".join(f["message"] for f in rep["findings"] if f["severity"] == "error"))
        tmp = signed_dir / f".{base}.unsigned.shortcut"
        tmp.write_bytes(data)
        out = signed_dir / f"{base}.shortcut"
        signing.sign(str(tmp), str(out), mode)
        tmp.unlink(missing_ok=True)
        path.unlink()
        _log(f"signed {out.name}")
        if open_in_app:
            signing.open_in_shortcuts_app(str(out))
        return out
    except (SpecError, ValueError, RuntimeError, OSError, json.JSONDecodeError, plistlib.InvalidFileException) as e:
        failed_dir.mkdir(parents=True, exist_ok=True)
        dest = failed_dir / name
        shutil.move(str(path), dest)
        (failed_dir / (name + ".log")).write_text(str(e), encoding="utf-8")
        _log(f"failed {name}: {e}")
        return None


def watch(inbox: str | Path = DEFAULT_INBOX, *, interval: float = 2.0, mode: str = "anyone",
          open_in_app: bool = False, once: bool = False) -> None:
    if not signing.can_sign():
        raise signing.SigningUnavailable("mac watch needs macOS with the `shortcuts` CLI")
    inbox = Path(inbox).expanduser()
    signed_dir, failed_dir = inbox / "Signed", inbox / "Failed"
    for d in (inbox, signed_dir):
        d.mkdir(parents=True, exist_ok=True)
    _log(f"watching {inbox}  ->  {signed_dir}")
    seen: dict[Path, float] = {}
    passes = 0
    while True:
        passes += 1
        for p in sorted(inbox.iterdir()):
            if not p.is_file() or p.name.startswith(".") or not p.name.endswith((".json", ".shortcut")):
                continue
            size = p.stat().st_size
            if seen.get(p) != size:  # wait until the file stops growing (iCloud downloads)
                seen[p] = size
                continue
            seen.pop(p, None)
            process_file(p, signed_dir, failed_dir, mode=mode, open_in_app=open_in_app)
        if once and passes >= 2:
            return
        if once:
            continue
        time.sleep(interval)


def _executable() -> str:
    exe = shutil.which("shortcut-forge")
    if exe and "/.cache/uv/" not in exe:
        return exe
    raise RuntimeError("Install the CLI permanently first so launchd can find it:\n"
                       "  uv tool install shortcut-forge   (or: pipx install shortcut-forge)")


def install_agent(inbox: str | Path = DEFAULT_INBOX, mode: str = "anyone") -> Path:
    if platform.system() != "Darwin":
        raise RuntimeError("launchd agents are macOS only")
    log_dir = Path.home() / "Library" / "Logs"
    plist = {
        "Label": LABEL,
        "ProgramArguments": [_executable(), "mac", "watch", "--inbox", str(Path(inbox).expanduser()), "--mode", mode],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(log_dir / "shortcut-forge.log"),
        "StandardErrorPath": str(log_dir / "shortcut-forge.log"),
        "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"},
    }
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    with open(AGENT, "wb") as f:
        plistlib.dump(plist, f)
    subprocess.run(["launchctl", "unload", str(AGENT)], capture_output=True)
    subprocess.run(["launchctl", "load", "-w", str(AGENT)], check=True)
    return AGENT


def uninstall_agent() -> None:
    if AGENT.exists():
        subprocess.run(["launchctl", "unload", "-w", str(AGENT)], capture_output=True)
        AGENT.unlink()


def main_watch(argv: list[str]) -> None:  # pragma: no cover - thin wrapper
    import argparse
    ap = argparse.ArgumentParser(prog="shortcut-forge mac watch")
    ap.add_argument("--inbox", default=str(DEFAULT_INBOX))
    ap.add_argument("--mode", default="anyone")
    ap.add_argument("--open", action="store_true", help="open each signed file in the Shortcuts app")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    try:
        watch(a.inbox, mode=a.mode, open_in_app=a.open, once=a.once)
    except KeyboardInterrupt:
        sys.exit(0)
