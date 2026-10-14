<p align="center">
  <img src="docs/assets/hero.svg" alt="shortcut-forge" width="100%">
</p>

<h1 align="center">shortcut-forge</h1>

<p align="center">
  <b>話しかけるだけで、Claude が iPhone で本当に動くショートカットを作ります。</b><br>
  MCP サーバー · Claude Code プラグイン · Claude Desktop 拡張 · Python DSL · iOS 27 対応
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

---

LLM にショートカットを頼むと、手で打ち込む手順のリストか、読み込めるのに実行すると
*「このアクションの各パラメータの値を選択してください」* で止まるファイルが返ってきます。

**shortcut-forge はその溝を埋めます。** Claude がショートカットを JSON で設計し、shortcut-forge が
**実機で検証済みの構造だけ**で `.shortcut` を生成、実機デバッグで見つけた 14 の失敗パターンでリントし、
Mac で署名して iPhone にそのまま読み込める形にします。

```text
あなた:  「サプリを飲むたびにヘルスケアに記録して、今日のリマインダーを完了、
          明日の分も作って。でも重複は絶対ダメ」
Claude:  → shortcut_from_template("supplement-tracker", …)
         ✓ 750 アクション · リントエラー 0 · 署名済み
         → ~/Downloads/shortcut-forge/Supplement Check.shortcut   (AirDrop で iPhone へ)
```

## なぜ作ったか

家族用のサプリ記録ショートカット（iOS 27 の保存コンテンツ、ヘルスケア、リマインダー、Apple Intelligence）を
Claude に plist で生成させたところ、動くまでに **読み込み → 実行 → スクショを十数回** 繰り返しました。
どの失敗もビルド時には何も起きませんでした。

| 書いたもの | iPhone の挙動 |
|---|---|
| 変数をそのまま保存コンテンツへ | エラーなしで**何も保存されない** |
| B12「77.4 mcg」をヘルスケアへ | **77,400,000 mcg** と記録（単位をグラムとして解釈） |
| `もし <辞書の値> が "昼"` | 比較欄が空になり実行中断 |
| 存在しないキーを削除 | エラー 16 |
| 見つけたリマインダーを完了に | 実行中に項目選択が出る |
| 明日のリマインダーを作成 | 実行のたびに重複 |

これらは**ビルダーでは作れず、リンターはどのショートカットでも検出**します。詳細は
[PITFALLS.md](src/shortcut_forge/data/PITFALLS.md)。

## インストール

### Claude Code（プラグイン：MCP + スキル + `/shortcut`）

```bash
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
```

### Claude Desktop

[Releases](https://github.com/Hyunki6040/shortcut-forge/releases) の `shortcut-forge.mcpb` をダブルクリック、
または `claude_desktop_config.json` に追加：

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

Mac では署名まで自動です。

### Python / CLI

```bash
pip install git+https://github.com/Hyunki6040/shortcut-forge
shortcut-forge template supplement-tracker --sign
shortcut-forge lint "My Shortcut.unsigned.shortcut"
```

```python
from shortcut_forge import Shortcut

sc = Shortcut("Hello")
name = sc.ask("お名前は？")
sc.notify("こんにちは", f"ようこそ、{name}")
sc.storage_set("last_name", name)   # iOS 27 保存コンテンツ
sc.health_log("Vitamin D", "50")    # mcg → mg を自動変換
sc.save("Hello.unsigned.shortcut")
```

## MCP ツール

`shortcut_build` · `shortcut_from_template` · `shortcut_lint` · `shortcut_inspect` · `shortcut_sign` · `shortcut_reference`

## コントリビュート

一番うれしいのは**新しい落とし穴**の報告です。読み込めるのに実機で失敗するショートカットを見つけたら、
エラーのスクショと最小の再現スペックを Issue へ。リントルールとビルダー修正にします。

MIT ライセンス。Apple・Anthropic とは無関係です。役に立ったら ⭐ をお願いします。
