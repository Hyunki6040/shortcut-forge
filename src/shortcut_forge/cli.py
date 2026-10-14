"""Command line: shortcut-forge build|template|lint|inspect|sign"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, sign as signing, templates
from .inspect import outline_file
from .lint import lint_file, summarize
from .spec import build_from_spec


def _emit(sc, out: str, do_sign: bool, mode: str) -> int:
    sc.save(out)
    rep = summarize(lint_file(out))
    for f in rep["findings"]:
        print(f"[{f['severity']}] {f['rule']} #{f['index']} {f['action']}: {f['message']}", file=sys.stderr)
    print(f"wrote {out} ({len(sc.actions)} actions, {rep['errors']} errors, {rep['warnings']} warnings)")
    if do_sign:
        if rep["errors"]:
            print("not signing: fix lint errors first", file=sys.stderr)
            return 1
        signed = signing.sign(out, out.replace(".unsigned", "") if ".unsigned" in out else None, mode)
        print(f"signed {signed}")
    return 1 if rep["errors"] else 0


def main(argv: list[str] | None = None) -> int:
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
    a = ap.parse_args(argv)

    if a.cmd == "build":
        with open(a.spec, encoding="utf-8") as f:
            sc = build_from_spec(json.load(f))
        return _emit(sc, a.out or sc.name + ".unsigned.shortcut", a.sign, a.mode)
    if a.cmd == "template":
        mod = templates.get(a.name)
        if a.print_example:
            print(json.dumps(mod.EXAMPLE_CONFIG, ensure_ascii=False, indent=2))
            return 0
        cfg = mod.EXAMPLE_CONFIG
        if a.config:
            with open(a.config, encoding="utf-8") as f:
                cfg = json.load(f)
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
    return 2


if __name__ == "__main__":
    sys.exit(main())
