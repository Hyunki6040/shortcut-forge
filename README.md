<!-- mcp-name: io.github.Hyunki6040/shortcut-forge -->
<p align="center">
  <img src="docs/assets/hero.svg" alt="shortcut-forge: say it, Claude builds it, your iPhone runs it" width="100%">
</p>

<h1 align="center">shortcut-forge</h1>

<p align="center">
  <b>Let Claude build real Apple Shortcuts that actually run on your iPhone.</b><br>
  MCP server · Claude Code plugin · Claude Desktop extension · Python DSL · iOS 27 aware
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/Hyunki6040/shortcut-forge/actions"><img src="https://img.shields.io/github/actions/workflow/status/Hyunki6040/shortcut-forge/ci.yml?label=tests" alt="tests"></a>
  <img src="https://img.shields.io/badge/iOS-27-black?logo=apple" alt="iOS 27">
  <img src="https://img.shields.io/badge/MCP-server-8A2BE2" alt="MCP">
  <img src="https://img.shields.io/badge/Claude-plugin-D97757" alt="Claude plugin">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
</p>

---

Ask any LLM for an Apple Shortcut and you get one of two things: a list of steps to tap in by hand, or a
plist that imports fine and then dies on the phone with *"Choose a value for each parameter of this action."*

**shortcut-forge closes that gap.** Claude describes the shortcut as JSON. shortcut-forge turns it into a
`.shortcut` file using only shapes that have been verified on a real iPhone, lints it against 14 failure
patterns that each cost a debugging round, and signs it with your Mac so the iPhone can import it.

```text
You:     "Every time I take my vitamins, log them to Apple Health, tick off today's reminder
          and set up tomorrow's — but never create duplicates."
Claude:  → shortcut_from_template("supplement-tracker", …)
         ✓ 750 actions · 0 lint errors · signed
         → ~/Downloads/shortcut-forge/Supplement Check.shortcut   (AirDrop it to your phone)
```

## Why this exists

I built a two-person supplement tracker as a Shortcut, iOS 27 Stored Content, Apple Health, Reminders and
Apple Intelligence included, by having Claude generate the plist. It took **more than a dozen import → run →
screenshot rounds** to get right. Every one of those failures was silent at build time:

| What we wrote | What the iPhone did |
|---|---|
| Stored Content set from a variable | Saved **nothing**, no error |
| Health sample "77.4 mcg" of B12 | Logged **77,400,000 mcg** (the unit is read as grams) |
| `If <dictionary value> is "Lunch"` | Comparison field empty → run aborted |
| Delete a stored key that isn't there | Error 16 |
| Mark found reminders as done | A picker popped up mid-run |
| Create tomorrow's reminder | Duplicates every time you ran it |

All of these are now **impossible to produce with the builder and detected by the linter** in any shortcut.
The full field notes are in [PITFALLS.md](src/shortcut_forge/data/PITFALLS.md).

## Install

### Claude Code (plugin: MCP + skill + `/shortcut` command)

```bash
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
```

Then: `/shortcut-forge:shortcut log a glass of water and tell me today's total`

### Claude Desktop

Download `shortcut-forge.mcpb` from [Releases](https://github.com/Hyunki6040/shortcut-forge/releases) and
double-click it, or add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "shortcut-forge": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Hyunki6040/shortcut-forge", "shortcut-forge-mcp"]
    }
  }
}
```

On a Mac, signing happens automatically. Files land in `~/Downloads/shortcut-forge/`.

### Any MCP client / remote connector

```bash
uvx --from git+https://github.com/Hyunki6040/shortcut-forge shortcut-forge-mcp          # stdio
uvx --from git+https://github.com/Hyunki6040/shortcut-forge shortcut-forge-mcp --http   # streamable HTTP
```

### Python library / CLI

```bash
pip install git+https://github.com/Hyunki6040/shortcut-forge
shortcut-forge template supplement-tracker --sign
shortcut-forge build examples/hello.json --sign
shortcut-forge lint "My Shortcut.unsigned.shortcut"
```

## Use it

**In plain language** (Claude Desktop / Claude Code):

- "Make a shortcut that asks how I slept, stores it, and every Sunday has Apple Intelligence summarise the week."
- "Water logger with 200/350/500 mL buttons that logs to Health and shows today's total."
- "Here's my exported shortcut, why does it crash?" → `shortcut_lint` + `shortcut_inspect`

**In Python**: variables work in f-strings.

```python
from shortcut_forge import Shortcut

sc = Shortcut("Hello")
name = sc.ask("What's your name?")
with sc.if_(name, "contains", "Claude") as br:
    sc.notify("Hi twin", f"Nice to meet another Claude, {name}")
    br.otherwise()
    sc.notify("Hi", f"Welcome, {name}")
sc.storage_set("last_name", name)          # iOS 27 Stored Content, done right
sc.health_log("Vitamin D", "50")           # mcg → mg handled for you
sc.save("Hello.unsigned.shortcut")
```

**As JSON** (what the MCP tools accept):

```json
{"name": "Hello", "actions": [
  {"ask": "What's your name?", "as": "name"},
  {"if": ["{{name}}", "contains", "Claude"],
   "then": [{"notify": "Hi twin", "body": "{{name}}"}],
   "else": [{"notify": "Hi", "body": "Welcome, {{name}}"}]}
]}
```

## MCP tools

| Tool | What it does |
|---|---|
| `shortcut_build` | JSON spec → `.shortcut`, always linted, optionally signed |
| `shortcut_from_template` | `supplement-tracker`, `water-log` |
| `shortcut_lint` | 14 rules (SF000–SF013) for any unsigned shortcut |
| `shortcut_inspect` | Indented outline of a shortcut (debug exported files) |
| `shortcut_sign` | `shortcuts sign` wrapper, verifies the `AEA1` header |
| `shortcut_reference` | spec · pitfalls · lint-rules · health-types · templates · ios27 |

## Templates

**supplement-tracker**: multi-user, one shortcut for the whole family.
First run asks who's using the device; settings live in iOS 27 Stored Content and can be edited from a ⚙ menu.
The list shows `✓ done` / `▶ now` / `missed`, so a forgotten lunch dose can still be logged at night.
It logs every nutrient to Apple Health, completes today's reminder for that slot, creates **tomorrow's
reminders for every slot only if they don't exist yet**, and gives you a 7-day report written by Apple
Intelligence. Korean and English UI.

**water-log**: one tap, Health logging, daily total.

## iOS 27 support

| Feature | Status |
|---|---|
| Stored Content (get/set/delete, global scope) | verified on device |
| Use Model (Apple Intelligence) | verified on device |
| Find / complete / add Reminders with alerts | verified on device |
| Log Health Sample (dietary nutrients) | verified on device |
| Log Health Sample (water, body metrics) | modelled, reports welcome |

## How it works

```
prompt ─► Claude ─► JSON spec ─► builder (field-tested shapes) ─► lint (14 rules) ─► shortcuts sign (macOS) ─► AirDrop
```

- `refs.py`: WF token strings vs attachments, UTF-16 offsets (emoji-safe), f-string variable embedding
- `builder.py`: the DSL. Every helper encodes one on-device lesson
- `lint.py`: the same lessons as static checks, for files from anywhere
- `sign.py`: macOS signing, headless

## Contributing

The most valuable contribution is **a new pitfall**: a shortcut that imports fine but fails on device.
Open an issue with the error screenshot and the smallest spec that reproduces it; it becomes a lint rule and a
builder fix. Device reports for "modelled" features are just as welcome.

## License

MIT. Not affiliated with Apple or Anthropic. "Shortcuts" is a trademark of Apple Inc.

If this saved you a round of screenshots, a ⭐ helps others find it.
