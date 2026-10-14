# AGENTS.md — for Codex, Claude Code and other coding agents

This repo is **shortcut-forge**, an Apple Shortcuts MCP server + Python DSL.

## When the user wants a shortcut
- Use the `shortcut-forge` MCP tools if available (`shortcut_library` → `shortcut_build` → fix lint → sign on macOS).
- Without MCP: write a JSON spec (see `prompts/LLM_PROMPT.md`) and run
  `uv run shortcut-forge build spec.json --sign` (macOS) or without `--sign` elsewhere.
- Never claim a shortcut works on a device until the user confirms a run.

## When changing the code
- `uv run --extra dev pytest -q` must pass; `uv run shortcut-forge library check` must be all ✓.
- A builder change that encodes a device lesson needs a lint rule in `lint.py`, a row in
  `src/shortcut_forge/data/PITFALLS.md` and a test.
- Mark features "verified" in `src/shortcut_forge/data/IOS27.md` only after a real device run.
- No personal data in `library/` (no real names, no health details beyond generic doses).
