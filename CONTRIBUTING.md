# Contributing

1. `uv run --extra dev pytest -q` must pass.
2. Every builder change that encodes a device lesson needs: a lint rule (or an existing rule id) in `lint.py`,
   a row in `src/shortcut_forge/data/PITFALLS.md`, and a test that the builder output is lint-clean.
3. Mark features "verified" in `IOS27.md` only after a run on a real device; say which device and OS.
4. Keep personal data out of examples and templates (no real names, no health details).
