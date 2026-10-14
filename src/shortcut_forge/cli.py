"""Command line.

  shortcut-forge mcp [--http]                       run the MCP server (same as shortcut-forge-mcp)
  shortcut-forge build spec.json [--sign]           JSON spec -> .shortcut
  shortcut-forge template NAME [--config c.json]    ready-made templates
  shortcut-forge lint FILE | inspect FILE | sign FILE
  shortcut-forge publish spec.json --version 1.2.0 --base-url URL   signed file + update manifest
  shortcut-forge library list|check|build|index|add
  shortcut-forge mac watch|install-agent|uninstall-agent
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import __version__, library, sign as signing, templates
from .inspect import outline_file
from .lint import lint_file, summarize
from .spec import build_from_spec


def _emit(sc, out: str, do_sign: bool, mode: str) -> int:
    sc.save(out)
    rep = summarize(lint_file(out))
    for f in rep["findings"]:
        if f["severity"] != "info":
            print(f"[{f['severity']}] {f['rule']} #{f['index']} {f['action']}: {f['message']}", file=sys.stderr)
    print(f"✓ wrote {out}  ({len(sc.actions)} actions · {rep['errors']} errors · {rep['warnings']} warnings)")
    if do_sign:
        if rep["errors"]:
            print("✗ not signing: fix lint errors first", file=sys.stderr)
            return 1
        signed = signing.sign(out, out.replace(".unsigned", "") if ".unsigned" in out else None, mode)
        print(f"✓ signed {signed}  (AirDrop it, or open it on iPhone from iCloud Drive)")
    return 1 if rep["errors"] else 0


def _publish(a) -> int:
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    base = a.base_url.rstrip("/") + "/"
    spec["version"] = a.version
    spec.setdefault("update_manifest", base + "manifest.json")
    sc = build_from_spec(spec)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    unsigned = out_dir / f".{sc.name}.unsigned.shortcut"
    sc.save(str(unsigned))
    rep = summarize(lint_file(str(unsigned)))
    if rep["errors"]:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 1
    signed = out_dir / f"{sc.name}.shortcut"
    signing.sign(str(unsigned), str(signed), a.mode)
    unsigned.unlink()
    manifest = {"name": sc.name, "version": a.version, "url": base + signed.name.replace(" ", "%20"),
                "sha256": hashlib.sha256(signed.read_bytes()).hexdigest(), "notes": a.notes or ""}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {signed}\n✓ {out_dir / 'manifest.json'}\nUpload both to {base} — installed copies "
          f"(built with update_manifest) will offer the update within a day.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["mcp"]:  # `uvx shortcut-forge mcp [--http ...]`
        from . import server
        sys.argv = ["shortcut-forge-mcp", *argv[1:]]
        server.main()
        return 0
    if argv[:2] == ["mac", "watch"]:
        from .mac import main_watch
        main_watch(argv[2:])
        return 0
    ap = argparse.ArgumentParser(prog="shortcut-forge", description="Build, lint and sign Apple Shortcuts.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build from a JSON spec")
    b.add_argument("spec")
    t = sub.add_parser("template", help="build from a template")
    t.add_argument("name", choices=list(templates.TEMPLATES))
    t.add_argument("--config", help="JSON config file (default: example config)")
    t.add_argument("--print-example", action="store_true")
    for p in (b, t):
        p.add_argument("-o", "--out", default=None)
        p.add_argument("--sign", action="store_true")
        p.add_argument("--mode", default="anyone")
    sub.add_parser("lint").add_argument("path")
    sub.add_parser("inspect").add_argument("path")
    s = sub.add_parser("sign")
    s.add_argument("path")
    s.add_argument("-o", "--out")
    s.add_argument("--mode", default="anyone")
    pb = sub.add_parser("publish", help="signed file + manifest.json for in-shortcut update checks")
    pb.add_argument("spec")
    pb.add_argument("--version", required=True)
    pb.add_argument("--base-url", required=True, help="where you will host the files (GitHub raw, Pages, S3...)")
    pb.add_argument("--out", default="dist")
    pb.add_argument("--notes", default="")
    pb.add_argument("--mode", default="anyone")
    lib = sub.add_parser("library", help="community library tools")
    lsub = lib.add_subparsers(dest="lcmd", required=True)
    for n in ("list", "check", "index"):
        x = lsub.add_parser(n)
        x.add_argument("--root", default=None)
    lb = lsub.add_parser("build")
    lb.add_argument("--root", default=None)
    lb.add_argument("--sign", action="store_true")
    lb.add_argument("--only", nargs="*")
    la = lsub.add_parser("add")
    la.add_argument("slug")
    la.add_argument("--spec", required=True)
    la.add_argument("--name", required=True)
    la.add_argument("--description", required=True)
    la.add_argument("--description-ko", default="")
    la.add_argument("--category", required=True)
    la.add_argument("--author", required=True)
    la.add_argument("--tags", default="")
    la.add_argument("--root", default="library")
    mac = sub.add_parser("mac", help="macOS automation (watch folder, launchd agent)")
    msub = mac.add_subparsers(dest="mcmd", required=True)
    mi = msub.add_parser("install-agent")
    mi.add_argument("--inbox", default=None)
    mi.add_argument("--mode", default="anyone")
    msub.add_parser("uninstall-agent")
    msub.add_parser("watch")  # handled above
    a = ap.parse_args(argv)

    if a.cmd == "build":
        sc = build_from_spec(json.loads(Path(a.spec).read_text(encoding="utf-8")))
        return _emit(sc, a.out or sc.name + ".unsigned.shortcut", a.sign, a.mode)
    if a.cmd == "template":
        mod = templates.get(a.name)
        if a.print_example:
            print(json.dumps(mod.EXAMPLE_CONFIG, ensure_ascii=False, indent=2))
            return 0
        cfg = json.loads(Path(a.config).read_text(encoding="utf-8")) if a.config else mod.EXAMPLE_CONFIG
        sc = mod.build(cfg)
        return _emit(sc, a.out or sc.name + ".unsigned.shortcut", a.sign, a.mode)
    if a.cmd == "lint":
        rep = summarize(lint_file(a.path))
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 1 if rep["errors"] else 0
    if a.cmd == "inspect":
        print(outline_file(a.path))
        return 0
    if a.cmd == "sign":
        print(signing.sign(a.path, a.out, a.mode))
        return 0
    if a.cmd == "publish":
        return _publish(a)
    if a.cmd == "library":
        if a.lcmd == "list":
            for row in library.as_listing(library.discover(a.root)):
                print(f"{row['slug']:<28} {row['category']:<13} {row['name']}")
            return 0
        if a.lcmd in ("check", "build"):
            rows = library.build_all(a.root, sign=getattr(a, "sign", False), only=getattr(a, "only", None))
            bad = 0
            for r in rows:
                flag = "✓" if not r["errors"] and not r["meta_errors"] else "✗"
                bad += flag == "✗"
                extra = f" signed→{Path(r['signed']).name}" if r.get("signed") else ""
                print(f"{flag} {r['slug']:<28} errors={r['errors']} warnings={r['warnings']} {r['meta_errors'] or ''}{extra}")
            return 1 if bad else 0
        if a.lcmd == "index":
            library.write_index(a.root)
            print("✓ library/INDEX.md")
            return 0
        if a.lcmd == "add":
            meta = {"name": a.name, "description": a.description, "description_ko": a.description_ko,
                    "category": a.category, "author": a.author, "tags": [t for t in a.tags.split(",") if t]}
            d = library.scaffold(a.root, a.slug, json.loads(Path(a.spec).read_text(encoding="utf-8")), meta)
            print(f"✓ created {d}. Next: shortcut-forge library check && open a PR")
            return 0
    if a.cmd == "mac":
        from . import mac as macmod
        if a.mcmd == "install-agent":
            p = macmod.install_agent(a.inbox or macmod.DEFAULT_INBOX, a.mode)
            print(f"✓ launchd agent installed: {p}\n  drop specs into {a.inbox or macmod.DEFAULT_INBOX}")
            return 0
        if a.mcmd == "uninstall-agent":
            macmod.uninstall_agent()
            print("✓ agent removed")
            return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
