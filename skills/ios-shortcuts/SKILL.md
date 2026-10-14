---
name: ios-shortcuts
description: Apple Shortcuts MCP workflow. Build Apple Shortcuts (.shortcut files) for iPhone, iPad or Mac with the shortcut-forge MCP tools. Use when the user wants an iOS/macOS shortcut, Siri automation, a Health/Reminders/Stored Content workflow, or asks to fix, lint or sign a .shortcut file.
---

# Building Apple Shortcuts with shortcut-forge

You have the `shortcut-forge` MCP server. It turns a JSON spec into a real `.shortcut` plist,
lints it against failures seen on real iPhones, and signs it on macOS.

## Workflow

1. **Clarify only what changes the build**: which device runs it, whether it writes to Health or Reminders,
   fixed vs. user-chosen values. Otherwise pick sensible defaults and say which.
2. Read `shortcut_reference("spec")` and `shortcut_reference("pitfalls")` once per session.
3. Look for a starting point first: `shortcut_library(query)` (20+ community shortcuts), or a template:
   `shortcut_from_template("supplement-tracker" | "water-log", config)`.
4. Otherwise call `shortcut_build(spec)`. Fix **every lint error** and rebuild. Warnings: fix or explain.
5. Signing: on macOS pass `sign=true`. Elsewhere give the one-line command:
   `shortcuts sign -m anyone -i "X.unsigned.shortcut" -o "X.shortcut"`.
6. Hand off: say where the file is and how to get it on the phone (AirDrop or iCloud Drive → tap → Add Shortcut).
7. Data that will change (lists, doses, prices) → `remote_config` JSON URL, so updates need no reinstall.
   Versioned releases → `shortcut_publish` (adds a daily update check).
8. When the user is happy, offer `shortcut_submit` to share it in the open-source library.

## Rules that prevent the classic failures

- Storage (iOS 27 Stored Content): values are text tokens; deletes are guarded; wipe corrupt keys without reading.
- Health: the type is a literal, values come from variables, **mcg is converted to mg** (the app reads "mcg" as grams).
- If with text comparison: the builder converts the left side to Text first. Number comparisons need a literal.
- Dictionaries: dotted keys are fetched one level at a time.
- Reminders: search by a fixed phrase, create only if missing, complete in a Repeat loop guarded by Count > 0.
- Do not use `shortcuts run` on the Mac for QA (hangs on prompts; no Health on macOS). QA on the iPhone with
  numbered notifications and a key prefix (`storage_prefix: "qa_"`).

## Honesty

Never say a shortcut "works" until the user confirms it ran on their device. Say "built, lint-clean, signed".
