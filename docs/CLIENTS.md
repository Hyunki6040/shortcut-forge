# Use shortcut-forge from any AI client

shortcut-forge is a standard MCP server (stdio + streamable HTTP), so it works anywhere MCP does.
Install-free: `uvx shortcut-forge mcp` runs the latest release from PyPI.

> Run it **on a Mac** if you want signed files straight away. On Linux/Windows you get unsigned files and a
> one-line command to sign them on a Mac (or let the Mac watch-folder agent do it, see below).

## Claude Code
```bash
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
# or MCP only:
claude mcp add shortcut-forge -- uvx shortcut-forge mcp
```

## Claude Desktop
Install `shortcut-forge.mcpb` from Releases (double-click), or `claude_desktop_config.json`:
```json
{ "mcpServers": { "shortcut-forge": { "command": "uvx", "args": ["shortcut-forge", "mcp"] } } }
```

## OpenAI Codex (CLI / IDE)
```bash
codex mcp add shortcut-forge -- uvx shortcut-forge mcp
```
or `~/.codex/config.toml`:
```toml
[mcp_servers.shortcut-forge]
command = "uvx"
args = ["shortcut-forge", "mcp"]
```
Then: *"Build me an Apple Shortcut that logs my coffee to Health and sign it."*
Working inside this repo? Codex also reads [AGENTS.md](../AGENTS.md).

## ChatGPT (custom connector / developer mode)
ChatGPT talks to remote MCP servers over HTTPS. On your Mac:
```bash
uvx shortcut-forge mcp --http --port 8765          # local server
cloudflared tunnel --url http://127.0.0.1:8765      # or: ngrok http 8765
```
Add the tunnel URL + `/mcp` as a connector in ChatGPT's developer-mode settings. Signing happens on your Mac;
files land in `~/Downloads/shortcut-forge`. Only expose the tunnel while you use it.

## No MCP at all (ChatGPT app, Gemini, any chatbot, even on your phone)
1. Paste [prompts/LLM_PROMPT.md](../prompts/LLM_PROMPT.md) as the system prompt / first message.
2. Ask for a shortcut. It answers with a JSON spec.
3. Save the JSON into **iCloud Drive › Shortcut Forge** from the Files app.
4. Your Mac (running `shortcut-forge mac install-agent`) signs it within seconds into **Shortcut Forge › Signed**.
5. Tap the signed file on your iPhone → Add Shortcut.

## Cursor / VS Code / Windsurf / Gemini CLI
All use the same shape:
```json
{ "mcpServers": { "shortcut-forge": { "command": "uvx", "args": ["shortcut-forge", "mcp"] } } }
```
(Cursor: `~/.cursor/mcp.json` · VS Code: `.vscode/mcp.json` with `"servers"` instead of `"mcpServers"` ·
Gemini CLI: `~/.gemini/settings.json`.)
