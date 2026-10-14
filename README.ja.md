<!-- mcp-name: io.github.Hyunki6040/shortcut-forge -->
<p align="center">
  <img src="docs/assets/hero.svg" alt="shortcut-forge: Apple Shortcuts MCP サーバー" width="100%">
</p>

<h1 align="center">shortcut-forge: iPhone で本当に動くショートカットを作る Apple Shortcuts MCP</h1>

<p align="center">
  <b>Claude・Codex・ChatGPT に話しかける → 署名済み <code>.shortcut</code> → iPhone でタップ。</b><br>
  Apple Shortcuts MCP · iOS ショートカット生成 · iOS 27 対応 · Mac 自動署名 · オープンなショートカットライブラリ
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center"><img src="docs/assets/demo.gif" alt="デモ" width="88%"></p>

## よくある声

> *「ChatGPT に頼んだら、手で打ち込む手順が 14 個返ってきた」*
> *「読み込めたのに、実行すると **『このアクションの各パラメータの値を選択してください』**」*
> *「iOS 27 の“説明してショートカット作成”は iPhone 15 Pro 以降のみ。変更内容をレビューもバージョン管理もできない」*
> *「見つかるショートカット MCP は既存のショートカットを**実行**するだけ」*
> *「家族用ショートカットを直すたびに全員が再ダウンロード」*

**shortcut-forge** は「こんなショートカットを作って」を、**実機で壊れるパターン（15 ルール）をチェック済みの署名付き
`.shortcut`** に変えます。Claude、Codex、ChatGPT、Cursor など MCP が使える場所ならどこでも動きます。

## インストール

```bash
# Claude Code
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
# OpenAI Codex
codex mcp add shortcut-forge -- uvx shortcut-forge mcp
# CLI
uv tool install shortcut-forge
```
Claude Desktop は Releases の `shortcut-forge.mcpb`。ChatGPT/Gemini は [docs/CLIENTS.md](docs/CLIENTS.md)。

## Mac 自動署名

```bash
shortcut-forge mac install-agent
```
`iCloud Drive/Shortcut Forge/` に JSON スペックを置くと、数秒で `Signed/` に署名済みファイルが出ます。
スマホの ChatGPT でスペックを作り「ファイル」に保存するだけで、同じ iPhone に追加できます。

## ライブラリ

朝のブリーフ、集中ブロック、議事録→タスク、クリップボード翻訳、カフェイン記録、家計簿、駐車位置、Webhook、
GitHub Issue、リモート JSON で更新されるランチ選び、そして本プロジェクトの原点である 1,073 アクションの
サプリ記録ショートカット。→ [library/INDEX.md](library/INDEX.md)

**作ったショートカットを共有してください。** AI に「shortcut-forge ライブラリに提出して」と言うだけ → [LIBRARY.md](LIBRARY.md)

## `.shortcut` ファイルとは

`.shortcut` はバイナリ plist のワークフローです。iOS 15 以降、共有ファイルは署名が必要（先頭バイト `AEA1` の
Apple Encrypted Archive）で、署名できるのは macOS の `shortcuts sign` だけです。`.wflow` は前身 Workflow アプリの形式。

## ロードマップ（協力募集）

最大の課題は**アップデート配布**です。修正のたびに再署名・再共有・全員が再ダウンロード。v0.2 で `remote_config`
（データ分離）、`update_check` + `publish`（自己アップデート通知）、署名フォルダを追加しました。次は「Shortcut Hub」：
ワンコマンド公開、常に最新を返す固定 URL、設定を保ったまま更新、チーム用署名リレー。→ [ROADMAP.md](ROADMAP.md)

MIT ライセンス。Apple・Anthropic とは無関係です。役に立ったら ⭐ をお願いします。
