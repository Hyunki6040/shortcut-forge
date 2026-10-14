<!-- mcp-name: io.github.Hyunki6040/shortcut-forge -->
<p align="center">
  <img src="docs/assets/hero.svg" alt="shortcut-forge: Apple Shortcuts MCP server. Say it, the AI builds it, your iPhone runs it." width="100%">
</p>

<h1 align="center">shortcut-forge: the Apple Shortcuts MCP server that ships shortcuts that actually run</h1>

<p align="center">
  <b>Describe an automation to Claude, Codex or ChatGPT → get a signed <code>.shortcut</code> file → tap it on your iPhone.</b><br>
  Apple Shortcuts MCP · iOS Shortcuts generator · Siri Shortcuts for AI agents · iOS 27 aware · macOS auto-signing · open shortcut library
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/Hyunki6040/shortcut-forge/actions"><img src="https://img.shields.io/github/actions/workflow/status/Hyunki6040/shortcut-forge/ci.yml?label=tests" alt="tests"></a>
  <a href="https://pypi.org/project/shortcut-forge/"><img src="https://img.shields.io/pypi/v/shortcut-forge?label=pypi" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/iOS-27-black?logo=apple" alt="iOS 27">
  <img src="https://img.shields.io/badge/MCP-server-8A2BE2" alt="MCP server">
  <img src="https://img.shields.io/badge/Claude%20%7C%20Codex%20%7C%20ChatGPT-ready-D97757" alt="Claude, Codex, ChatGPT">
  <a href="library/INDEX.md"><img src="https://img.shields.io/badge/library-20%2B%20shortcuts-2ea44f" alt="library"></a>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
</p>

<p align="center">
  <img src="docs/assets/demo.gif" alt="Demo: shortcut-forge builds, lints and signs an Apple Shortcut on a Mac, then it opens in the Shortcuts app" width="88%">
</p>

---

## The problem (you've probably said one of these)

> *"I asked ChatGPT for a shortcut and got fourteen steps to tap in by hand."*
>
> *"The file imported fine. Then: **'Choose a value for each parameter of this action.'**"*
>
> *"iOS 27 can build a shortcut from a description, but only on my iPhone 15 Pro, one shortcut at a time, and I can't
> review or version what it changed."*
>
> *"Every MCP server I found for Shortcuts only **runs** shortcuts I already have."*
>
> *"Every time I fix the family shortcut, everyone has to download it again."*

Apple Shortcuts is the most powerful automation layer on the iPhone, and still the hardest thing to get an AI to
produce. The file format is undocumented, a structurally valid plist can still break on the device, and nothing
catches the difference until you're staring at an error on your phone.

## The fix

**shortcut-forge** is an MCP server, a Claude plugin and a Python library that turns *"make me a shortcut that…"*
into a **signed `.shortcut` file that has been checked against the ways shortcuts really fail on iPhone.**

```text
You:     "Every time I take my vitamins, log them to Apple Health, tick off today's reminder
          and set up tomorrow's, but never create duplicates."
Claude:  → shortcut_library("supplements") → shortcut_from_template("supplement-tracker", …)
         ✓ 750 actions · 0 lint errors · signed on your Mac
         → ~/Downloads/shortcut-forge/Supplement Check.shortcut   (AirDrop / iCloud Drive → tap → Add)
```

| | Apple "Describe a Shortcut" (iOS 27) | Asking a chatbot | Other Shortcuts MCPs | **shortcut-forge** |
|---|---|---|---|---|
| Works from Claude, Codex, ChatGPT, Cursor… | – | ✓ | some | **✓** |
| No new iPhone required | needs iPhone 15 Pro+ / Apple silicon | ✓ | ✓ | **✓** |
| Output you can read, diff, version, review | – | text | varies | **JSON spec + plist** |
| Checked against real on-device failures | n/a (native) | – | structure only | **15 semantic rules** |
| Signed and importable on iPhone | ✓ (native) | – | rarely | **✓ auto on macOS** |
| Updates without re-downloading | – | – | – | **remote config + update check** |
| Shared, remixable library | – | – | – | **✓ 20+ entries** |

Apple's built-in builder is great for quick personal one-liners and lives right in the app; use it. Reach for
shortcut-forge when you want an AI *you already use* to build something bigger, reviewable and shareable.

## Install

**Claude Code** (plugin = MCP server + skill + `/shortcut` command)
```bash
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
```

**Claude Desktop**: double-click `shortcut-forge.mcpb` from [Releases](https://github.com/Hyunki6040/shortcut-forge/releases), or:
```json
{ "mcpServers": { "shortcut-forge": { "command": "uvx", "args": ["shortcut-forge-mcp"] } } }
```

**OpenAI Codex**
```bash
codex mcp add shortcut-forge -- uvx shortcut-forge-mcp
```

**ChatGPT, Gemini, any chatbot**: connect over HTTP (`shortcut-forge-mcp --http`) or, with no MCP at all, paste
[`prompts/LLM_PROMPT.md`](prompts/LLM_PROMPT.md) and drop the JSON it writes into the Mac watch folder (below).
Cursor, VS Code, Windsurf, Gemini CLI: see [docs/CLIENTS.md](docs/CLIENTS.md).

**Python / CLI**
```bash
uv tool install shortcut-forge        # or: pipx install shortcut-forge
shortcut-forge template supplement-tracker --sign
```

## Mac auto-signing: drop a spec, get a shortcut

iOS only imports signed shortcuts, and only a Mac can sign them. shortcut-forge makes that invisible:

```bash
shortcut-forge mac install-agent      # launchd agent, starts at login
```

```
iCloud Drive/Shortcut Forge/          ← drop *.json specs or *.unsigned.shortcut (from any device or AI)
iCloud Drive/Shortcut Forge/Signed/   ← signed .shortcut appears in seconds → open it on your iPhone
iCloud Drive/Shortcut Forge/Failed/   ← anything that failed lint, with a .log explaining why
```

Ask ChatGPT on your phone for a spec, save it to Files, and the shortcut is ready on the same phone before you
finish your coffee. In Claude Desktop / Claude Code on a Mac, signing happens inside the tool call.

## What people build with it

From the [Open Shortcut Library](library/INDEX.md). Every one is a readable spec, lint-clean in CI.

| | Shortcut | What it does |
|---|---|---|
| 🌤 | [Morning Brief](library/morning-brief) | Your messy thoughts → a 3-line plan by Apple Intelligence → a reminder |
| 🎯 | [Focus Block](library/focus-block) | Blocks 25/50/90 min on your calendar from right now |
| ✅ | [Meeting → Action Items](library/meeting-to-actions) | Notes in, reminders out, summary on the clipboard |
| 🌐 | [Clipboard Translate](library/clipboard-translate) | Translate whatever you copied, result back on the clipboard |
| ☕️ | [Caffeine Log](library/caffeine-log) | One tap → Apple Health, warns past 400 mg |
| 💸 | [Expense Log](library/expense-log) | Amount + category → CSV in Stored Content → paste into your sheet |
| 🅿️ | [Parking Spot](library/parking-spot) | Save where you parked, open it in Maps later |
| 📡 | [Webhook Trigger](library/webhook-trigger) | POST JSON to n8n / Zapier / Home Assistant |
| 🐙 | [GitHub Issue](library/github-issue) | File an issue from your phone |
| 🍱 | [Lunch Picker](library/lunch-picker-remote) | Reads options from a JSON URL: edit once, every phone updates, no reinstall |
| 💊 | [**영양제 체크 (the original)**](library/supplement-check-original) | The real 1,073-action shortcut that started this project. Two people, ten time slots, alternate-day doses, Health + Reminders + Apple Intelligence |

…and [more](library/INDEX.md): mood journal, sleep diary, grocery list, weather voice brief, low-battery nudge, water log.

**Built something? [Share it →](LIBRARY.md)** Tell your AI *"submit this to the shortcut-forge library"*.

## Use it

**Plain language** in any MCP client:
- *"Make a shortcut that asks how I slept and every Sunday has Apple Intelligence summarise the week."*
- *"Start from the library's expense log, but in won and with my categories."*
- *"Here's my exported shortcut. Why does it crash?"* → `shortcut_lint` + `shortcut_inspect`

**Python**: variables work in f-strings.
```python
from shortcut_forge import Shortcut

sc = Shortcut("Hello", version="1.0.0")
name = sc.ask("What's your name?")
with sc.if_(name, "contains", "Claude") as br:
    sc.notify("Hi twin", f"Nice to meet another Claude, {name}")
    br.otherwise()
    sc.notify("Hi", f"Welcome, {name}")
sc.storage_set("last_name", name)       # iOS 27 Stored Content, done right
sc.health_log("Vitamin D", "50")        # mcg → mg handled for you
sc.save("Hello.unsigned.shortcut")
```

**JSON** (what the MCP tools and chatbots write): 50+ step types, plus a `raw` escape hatch for any action.
```json
{"name": "Hello", "version": "1.0.0", "actions": [
  {"ask": "What's your name?", "as": "name"},
  {"if": ["{{name}}", "contains", "Claude"],
   "then": [{"notify": "Hi twin", "body": "{{name}}"}],
   "else": [{"notify": "Hi", "body": "Welcome, {{name}}"}]}
]}
```

## MCP tools

| Tool | What it does |
|---|---|
| `shortcut_build` | JSON spec → `.shortcut`, always linted, signed on macOS |
| `shortcut_library` | Browse / fetch 20+ community shortcuts as starting points |
| `shortcut_from_template` | `supplement-tracker` (multi-user), `water-log` |
| `shortcut_lint` | 15 rules (SF000–SF014) for any unsigned shortcut, including ones exported from the app |
| `shortcut_inspect` | Indented outline of a shortcut |
| `shortcut_sign` | `shortcuts sign` wrapper, verifies the `AEA1` header |
| `shortcut_publish` | Sign + `manifest.json` so installed copies can update themselves |
| `shortcut_submit` | Package your shortcut + PR commands for the library |
| `shortcut_llm_prompt` | System prompt for chatbots without MCP |
| `shortcut_reference` | spec · pitfalls · lint-rules · health-types · templates · library · ios27 |

## Field notes: why "it imported" isn't "it works"

We built a two-person tracker by having Claude generate the plist. It took more than a dozen
import → run → screenshot rounds. Every failure was invisible at build time:

| What we wrote | What the iPhone did | Rule |
|---|---|---|
| Stored Content set from a variable | Saved **nothing**, no error | SF001 |
| Health sample "77.4 mcg" of B12 | Logged **77,400,000 mcg** (the unit string is read as grams) | SF003 |
| `If <dictionary value> is "Lunch"` | Comparison field empty → run aborted | SF005 |
| Delete a stored key that isn't there | Error 16 | SF002 |
| Mark found reminders as done | A picker popped up mid-run | SF007 |
| Get Contents of URL on every run | Offline once → whole shortcut aborts | SF014 |
| Create tomorrow's reminder | Duplicates on every run | builder |

The builder can't produce these; the linter catches them in any shortcut. Full notes:
[PITFALLS.md](src/shortcut_forge/data/PITFALLS.md).

## What is a `.shortcut` file?

- A **`.shortcut`** file (not `.short` or `.shortcuts`) is an Apple Shortcuts workflow: a binary property list
  (`WFWorkflowActions`, `WFWorkflowIcon`, …) where every action is an identifier like
  `is.workflow.actions.gettext` plus parameters. Variables are "token strings" with UTF-16 offsets.
- Since iOS 15, shared shortcut files must be **signed**. A signed file is an Apple Encrypted Archive whose first
  bytes are `AEA1`. Unsigned plists import on a Mac but iOS refuses them.
- Signing modes: `anyone` (any device can import) or `people-who-know-me` (contacts only). Only macOS can sign
  (`shortcuts sign`), which is why shortcut-forge automates the Mac side.
- `.wflow` was the format of the old *Workflow* app that became Shortcuts; iCloud links (`icloud.com/shortcuts/…`)
  are snapshots created from the app and can't be generated or updated programmatically.

## FAQ

**Do I need a Mac?** To *sign*, yes (Apple's rule). Building and linting run anywhere; the watch-folder agent lets
one Mac sign for every device you own.
**Does my data leave my machine?** No. The server runs locally; nothing is uploaded. Library shortcuts that use
`remote_config` fetch only the JSON URL they name.
**Is this affiliated with Apple or Anthropic?** No. It is an independent open-source project.
**iOS 26 or older?** Most actions work; Stored Content needs iOS 27 and Use Model needs Apple Intelligence (the
linter flags these as SF013).

## Roadmap: the update problem (help wanted)

Today every shortcut fix means re-sign → re-share → everyone re-downloads and taps "Replace". v0.2 ships the first
answers (`remote_config` for data, `update_check` + `publish` for code, a signing watch folder). Next is a
**Shortcut Hub**: one-command publish to GitHub, a stable install URL that always serves the latest version,
settings that survive updates, a signing relay for teams, and an experimental loader pattern.
Read [ROADMAP.md](ROADMAP.md) and pick something. Device reports from real iPhones are the most valuable
contribution of all.

## Contributing

- **Share a shortcut** → [LIBRARY.md](LIBRARY.md)
- **Found a new way shortcuts break?** Open a *pitfall* issue with the error screenshot and the smallest spec; it
  becomes a lint rule and a builder fix.
- **Code** → [CONTRIBUTING.md](CONTRIBUTING.md) · agents read [AGENTS.md](AGENTS.md)

MIT licensed. Not affiliated with Apple Inc. or Anthropic. "Shortcuts" and "Siri" are trademarks of Apple Inc.

If shortcut-forge saved you a round of error screenshots, a ⭐ helps the next person find it.

<sub>Keywords: Apple Shortcuts MCP, iOS Shortcuts MCP server, Siri Shortcuts AI generator, create .shortcut file
programmatically, sign shortcut macOS CLI, Claude Shortcuts, Codex Shortcuts, ChatGPT Shortcuts, iOS 27 Shortcuts
Stored Content, Apple Health shortcut, shortcut library.</sub>
