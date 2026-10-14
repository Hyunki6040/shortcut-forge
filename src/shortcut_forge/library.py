"""Community shortcut library: discover, build, sign, index and publish entries.

Layout (one folder per shortcut):

    library/<slug>/
      meta.json                 name, description(_ko), author, category, tags, ios, verified_on
      shortcut.json             a JSON spec            (or)
      template.json             {"template": "...", "config": {...}}   (or)
      source.unsigned.shortcut  an exported/hand-built plist
      <Name>.shortcut           signed build (committed by maintainers, built on a Mac)
      manifest.json             {"version", "url", "sha256", ...}  -> read by update_check()
"""
from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
from urllib.parse import quote
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from . import sign as signing, templates
from .lint import lint_plist, summarize
from .spec import build_from_spec

REPO = "Hyunki6040/shortcut-forge"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main/library"
REQUIRED_META = ("name", "description", "author", "category")


@dataclass
class Entry:
    slug: str
    path: Path
    meta: dict
    kind: str  # spec | template | plist
    version: str = "1.0.0"
    findings: dict = field(default_factory=dict)

    @property
    def file_name(self) -> str:
        return re.sub(r'[\\/:*?"<>|]', "_", self.meta["name"]) + ".shortcut"


def default_root() -> Path:
    pkg = Path(str(resources.files("shortcut_forge")))
    for cand in (Path.cwd() / "library", pkg / "library", pkg.parent.parent / "library"):
        if cand.is_dir() and any(cand.glob("*/meta.json")):
            return cand
    raise FileNotFoundError("library folder not found (run from the repo or install the package)")


def discover(root: str | Path | None = None) -> list[Entry]:
    root = Path(root) if root else default_root()
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        mp = d / "meta.json"
        if not mp.exists():
            continue
        meta = json.loads(mp.read_text(encoding="utf-8"))
        if (d / "shortcut.json").exists():
            kind = "spec"
            version = json.loads((d / "shortcut.json").read_text(encoding="utf-8")).get("version", "1.0.0")
        elif (d / "template.json").exists():
            kind, version = "template", meta.get("version", "1.0.0")
        elif (d / "source.unsigned.shortcut").exists():
            kind, version = "plist", meta.get("version", "1.0.0")
        else:
            continue
        out.append(Entry(d.name, d, meta, kind, str(version)))
    return out


def validate_meta(meta: dict, slug: str) -> list[str]:
    errs = [f"meta.{k} is required" for k in REQUIRED_META if not meta.get(k)]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", slug):
        errs.append("slug must be lowercase letters, digits and dashes")
    return errs


def build_entry(e: Entry) -> bytes:
    if e.kind == "spec":
        sc = build_from_spec(json.loads((e.path / "shortcut.json").read_text(encoding="utf-8")))
        return sc.to_bytes()
    if e.kind == "template":
        t = json.loads((e.path / "template.json").read_text(encoding="utf-8"))
        return templates.get(t["template"]).build(t.get("config") or {}).to_bytes()
    return (e.path / "source.unsigned.shortcut").read_bytes()


def check(e: Entry) -> dict:
    data = build_entry(e)
    rep = summarize(lint_plist(plistlib.loads(data)))
    rep["meta_errors"] = validate_meta(e.meta, e.slug)
    e.findings = rep
    return rep


def build_all(root: str | Path | None = None, *, sign: bool = False, mode: str = "anyone",
              only: list[str] | None = None) -> list[dict]:
    results = []
    for e in discover(root):
        if only and e.slug not in only:
            continue
        rep = check(e)
        row = {"slug": e.slug, "errors": rep["errors"], "warnings": rep["warnings"], "meta_errors": rep["meta_errors"]}
        if sign and not rep["errors"] and not rep["meta_errors"]:
            tmp = e.path / ".build.unsigned.shortcut"
            tmp.write_bytes(build_entry(e))
            try:
                signed = e.path / e.file_name
                signing.sign(str(tmp), str(signed), mode)
                digest = hashlib.sha256(signed.read_bytes()).hexdigest()
                manifest = {"name": e.meta["name"], "version": e.version, "sha256": digest,
                            "url": f"{RAW_BASE}/{e.slug}/{quote(e.file_name)}",
                            "notes": e.meta.get("changelog", "")}
                (e.path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
                row["signed"] = str(signed)
            finally:
                tmp.unlink(missing_ok=True)
        results.append(row)
    return results


def write_index(root: str | Path | None = None, out: str | Path | None = None) -> str:
    root = Path(root) if root else default_root()
    entries = discover(root)
    cats: dict[str, list[Entry]] = {}
    for e in entries:
        cats.setdefault(e.meta.get("category", "other"), []).append(e)
    lines = ["# Shortcut Library", "",
             f"{len(entries)} community shortcuts built with shortcut-forge. Tap a signed file on your iPhone to add it.",
             "Want yours here? See [LIBRARY.md](../LIBRARY.md).", ""]
    for cat in sorted(cats):
        lines += [f"## {cat}", "", "| Shortcut | What it does | 설명 | Get | Verified |", "|---|---|---|---|---|"]
        for e in cats[cat]:
            signed = e.path / e.file_name
            get = f"[⬇︎ .shortcut]({e.slug}/{quote(e.file_name)})" if signed.exists() else \
                f"[spec]({e.slug}/)"
            ver = e.meta.get("verified_on") or "—"
            lines.append(f"| **{e.meta['name']}** · by @{e.meta['author']} | {e.meta['description']} | "
                         f"{e.meta.get('description_ko', '')} | {get} | {ver} |")
        lines.append("")
    text = "\n".join(lines)
    Path(out or root / "INDEX.md").write_text(text, encoding="utf-8")
    return text


def scaffold(root: str | Path, slug: str, spec: dict, meta: dict) -> Path:
    """Create library/<slug>/ with meta.json + shortcut.json (used by `library add` and the MCP tool)."""
    errs = validate_meta(meta, slug)
    if errs:
        raise ValueError("; ".join(errs))
    build_from_spec(spec)  # raises on invalid spec
    d = Path(root) / slug
    if d.exists():
        raise ValueError(f"{d} already exists")
    d.mkdir(parents=True)
    meta = {"slug": slug, "ios": "27", "verified_on": None, **meta}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / "shortcut.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return d


def submission_bundle(slug: str, spec: dict, meta: dict) -> dict:
    """Everything a contributor needs to open a PR, without touching their disk."""
    errs = validate_meta(meta, slug)
    sc = build_from_spec(spec)
    rep = summarize(sc.lint())
    meta = {"slug": slug, "ios": "27", "verified_on": None, **meta}
    return {
        "ok": not errs and not rep["errors"],
        "meta_errors": errs,
        "lint": rep,
        "files": {f"library/{slug}/meta.json": meta, f"library/{slug}/shortcut.json": spec},
        "how_to_submit": [
            f"gh repo fork {REPO} --clone && cd shortcut-forge",
            f"shortcut-forge library add {slug} --spec your_spec.json --name '{meta.get('name', '')}' "
            "--description '...' --category ... --author <github-handle>",
            "shortcut-forge library check",
            f"git checkout -b library/{slug} && git add library/{slug} && git commit -m 'library: add {slug}'",
            "gh pr create --fill --label library",
        ],
        "tip": "Run it on your iPhone first and put the device + iOS version in meta.verified_on.",
    }


def manifest_for(e: Entry) -> dict | None:
    p = e.path / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def as_listing(entries: list[Entry]) -> list[dict]:
    return [{"slug": e.slug, "name": e.meta["name"], "category": e.meta.get("category"),
             "description": e.meta.get("description"), "tags": e.meta.get("tags", []), "kind": e.kind,
             "verified_on": e.meta.get("verified_on"),
             "signed_file": f"{RAW_BASE}/{e.slug}/{quote(e.file_name)}" if (e.path / e.file_name).exists() else None}
            for e in entries]


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path
