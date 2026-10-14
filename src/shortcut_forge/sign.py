"""Signing and Mac-side helpers.

iOS only imports *signed* shortcut files. Signing needs macOS with the
`shortcuts` command-line tool (macOS 12+) and an iCloud account signed in.

Lessons:
- `shortcuts sign` works headless; a valid result starts with the bytes ``AEA1``.
- `shortcuts run` on a shortcut that asks questions (menus, Ask for Input) blocks
  forever in a headless shell, and Health actions do not exist on the Mac at
  all. Run behavioural QA on the iPhone, not via the CLI.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess

SIGNED_MAGIC = b"AEA1"
MODES = {"anyone": "anyone", "people-who-know-me": "people-who-know-me", "contacts": "people-who-know-me"}


class SigningUnavailable(RuntimeError):
    pass


def is_signed(path: str) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == SIGNED_MAGIC


def can_sign() -> bool:
    return platform.system() == "Darwin" and shutil.which("shortcuts") is not None


def sign(input_path: str, output_path: str | None = None, mode: str = "anyone", timeout: int = 120) -> str:
    """Sign ``input_path``. Returns the signed file path (``<name>.signed.shortcut`` by default)."""
    if not can_sign():
        raise SigningUnavailable(
            "Signing needs macOS with the `shortcuts` CLI. Options: run this MCP server on a Mac "
            "(Claude Desktop / Claude Code), or copy the unsigned file to a Mac and run "
            "`shortcuts sign -m anyone -i in.shortcut -o out.shortcut`.")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    if output_path is None:
        root, _ = os.path.splitext(input_path)
        output_path = root + ".signed.shortcut"
    tmp = output_path + ".tmp"
    proc = subprocess.run(["shortcuts", "sign", "-m", MODES[mode], "-i", input_path, "-o", tmp],
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not os.path.exists(tmp) or not is_signed(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"shortcuts sign failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
    os.replace(tmp, output_path)
    return output_path


def open_in_shortcuts_app(path: str) -> None:
    """Hand the file to the Shortcuts app on the Mac (shows the import sheet)."""
    if platform.system() != "Darwin":
        raise SigningUnavailable("Only available on macOS")
    subprocess.run(["open", "-a", "Shortcuts", path], check=True)
