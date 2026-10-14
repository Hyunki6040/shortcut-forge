<!-- mcp-name: io.github.Hyunki6040/shortcut-forge -->
<p align="center">
  <img src="docs/assets/hero.svg" alt="shortcut-forge：Apple Shortcuts MCP 服务器" width="100%">
</p>

<h1 align="center">shortcut-forge：能在 iPhone 上真正运行的 Apple Shortcuts MCP</h1>

<p align="center">
  <b>对 Claude、Codex 或 ChatGPT 说一句话 → 已签名的 <code>.shortcut</code> 文件 → 在 iPhone 上轻点添加。</b><br>
  Apple Shortcuts MCP · iOS 快捷指令生成器 · 支持 iOS 27 · Mac 自动签名 · 开放快捷指令库
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center"><img src="docs/assets/demo.gif" alt="演示" width="88%"></p>

## 你可能说过这些话

> *“让 ChatGPT 写快捷指令，结果给了我 14 个要手动点的步骤。”*
> *“文件导入成功，一运行就是 **‘请为此操作的每个参数选择一个值’**。”*
> *“iOS 27 能用描述生成快捷指令，但只支持 iPhone 15 Pro 及以上，而且没法审阅或做版本管理。”*
> *“找到的快捷指令 MCP 都只能**运行**已有的快捷指令。”*
> *“每改一次家庭快捷指令，全家都得重新下载。”*

**shortcut-forge** 把“帮我做一个快捷指令”变成**经过 15 条真机故障规则检查、已签名的 `.shortcut` 文件**。
支持 Claude、Codex、ChatGPT、Cursor 等所有 MCP 客户端。

## 安装

```bash
# Claude Code
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
# OpenAI Codex
codex mcp add shortcut-forge -- uvx shortcut-forge-mcp
# CLI
uv tool install shortcut-forge
```
Claude Desktop 用 Releases 中的 `shortcut-forge.mcpb`；ChatGPT / Gemini 见 [docs/CLIENTS.md](docs/CLIENTS.md)。

## Mac 自动签名

```bash
shortcut-forge mac install-agent
```
把 JSON spec 放进 `iCloud Drive/Shortcut Forge/`，几秒后 `Signed/` 里就会出现已签名文件。
在手机上用 ChatGPT 生成 spec 存到“文件”，同一台 iPhone 就能直接添加。

## 快捷指令库

晨间计划、专注时段、会议记录转待办、剪贴板翻译、咖啡因记录、记账、停车位置、Webhook、GitHub Issue、
从远程 JSON 自动更新的午餐选择器，以及本项目的起点：1,073 个操作的补剂打卡快捷指令。→ [library/INDEX.md](library/INDEX.md)

**欢迎分享你做的快捷指令。** 对 AI 说“提交到 shortcut-forge 库”即可 → [LIBRARY.md](LIBRARY.md)

## 什么是 `.shortcut` 文件

`.shortcut` 是二进制 plist 格式的工作流。自 iOS 15 起，分享的文件必须签名（以 `AEA1` 开头的 Apple Encrypted
Archive），且只能在 macOS 上用 `shortcuts sign` 签名。`.wflow` 是前身 Workflow 应用的格式。

## 路线图（欢迎参与）

最大的难题是**更新分发**：每次修改都要重新签名、重新分享、所有人重新下载。v0.2 加入了 `remote_config`（数据分离）、
`update_check` + `publish`（快捷指令自己提示更新）和签名监视文件夹。下一步是 “Shortcut Hub”：一条命令发布、
始终指向最新版本的固定链接、更新后保留设置、团队签名中继。→ [ROADMAP.md](ROADMAP.md)

MIT 许可。与 Apple、Anthropic 无关。觉得有用请点个 ⭐。
