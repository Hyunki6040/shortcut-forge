---
description: Turn a plain-language automation idea into a signed Apple Shortcut
argument-hint: "<what the shortcut should do>"
---

Build an Apple Shortcut for: $ARGUMENTS

Use the ios-shortcuts skill and the shortcut-forge MCP tools:
1. Propose the flow in 3-6 bullets (inputs, actions, where data is stored, what gets written to Health/Reminders).
2. Build it with `shortcut_build` (or `shortcut_from_template` if one fits), fix all lint errors.
3. Sign it if running on macOS, then tell me the file path and how to import it on my iPhone.
