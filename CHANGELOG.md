# Changelog

## 0.2.0 (2026-10-14)
- Generalised beyond health: URL/JSON (GET/POST, headers), clipboard, speak, share, wait, vibrate, calendar, location,
  weather, battery, open app, list, plus a `raw` escape hatch for any action (53 spec step types).
- `remote_config` (daily-cached JSON data) and `update_check` + `shortcut-forge publish` (self-update prompts).
- macOS automation: `shortcut-forge mac watch` / `install-agent` (iCloud Drive watch folder that signs anything dropped in).
- Open Shortcut Library: 20 entries incl. the original 1,073-action supplement tracker; `library` CLI; MCP tools
  `shortcut_library`, `shortcut_submit`, `shortcut_publish`, `shortcut_llm_prompt`.
- Codex / ChatGPT / Cursor / Gemini setup (docs/CLIENTS.md), AGENTS.md, chatbot prompt (prompts/LLM_PROMPT.md).
- New lint rule SF014 (network call on every run).

## 0.1.0 (2026-10-14)
- Builder DSL with field-tested shapes for Stored Content, Health, Reminders, Use Model, If/Menu/Repeat.
- Linter with 14 rules (SF000–SF013) from on-device failures.
- macOS signing wrapper (`shortcuts sign`, AEA1 check).
- MCP server (6 tools, 2 resources, 1 prompt), Claude Code plugin + marketplace, Claude Desktop MCPB manifest,
  MCP Registry `server.json`.
- Templates: supplement-tracker (multi-user, ko/en), water-log.
