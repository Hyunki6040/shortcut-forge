<p align="center">
  <img src="docs/assets/hero.svg" alt="shortcut-forge" width="100%">
</p>

<h1 align="center">shortcut-forge</h1>

<p align="center">
  <b>说一句话，Claude 就能做出在 iPhone 上真正能运行的快捷指令。</b><br>
  MCP 服务器 · Claude Code 插件 · Claude Desktop 扩展 · Python DSL · 支持 iOS 27
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

---

让 LLM 写快捷指令，通常只会得到两种结果：一份需要手动点选的步骤清单，或者一个能导入、
一运行就报 *“请为此操作的每个参数选择一个值”* 的文件。

**shortcut-forge 解决的就是这个问题。** Claude 用 JSON 描述快捷指令，shortcut-forge **只用在真机上验证过的结构**
生成 `.shortcut` 文件，用 14 条真机踩坑规则做静态检查，再通过 Mac 签名，让 iPhone 可以直接导入。

```text
你:      “每次吃完补剂就记到健康 App，完成今天的提醒事项，再建好明天的，但绝不能重复。”
Claude:  → shortcut_from_template("supplement-tracker", …)
         ✓ 750 个操作 · 0 个错误 · 已签名
         → ~/Downloads/shortcut-forge/Supplement Check.shortcut   （AirDrop 到手机）
```

## 为什么做这个

我让 Claude 生成一个家庭用的补剂打卡快捷指令（iOS 27 存储内容、健康、提醒事项、Apple Intelligence），
前后**导入 → 运行 → 截图了十几轮**才跑通，而每个错误在生成时都毫无征兆：

| 写法 | iPhone 上的结果 |
|---|---|
| 直接把变量存入“存储内容” | 不报错，但**什么也没存** |
| 向健康写入 B12 “77.4 mcg” | 记录成 **77,400,000 mcg**（单位被当作克） |
| `如果 <词典值> 是 "午餐"` | 比较栏为空，运行中断 |
| 删除不存在的存储键 | 错误 16 |
| 把找到的提醒事项标记完成 | 运行中弹出选择框 |
| 创建明天的提醒 | 每次运行都重复创建 |

现在这些情况**用构建器写不出来，检查器能在任何快捷指令里发现**。完整记录见
[PITFALLS.md](src/shortcut_forge/data/PITFALLS.md)。

## 安装

### Claude Code（插件：MCP + 技能 + `/shortcut` 命令）

```bash
/plugin marketplace add Hyunki6040/shortcut-forge
/plugin install shortcut-forge@shortcut-forge
```

### Claude Desktop

从 [Releases](https://github.com/Hyunki6040/shortcut-forge/releases) 下载 `shortcut-forge.mcpb` 双击安装，或在
`claude_desktop_config.json` 中加入：

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

在 Mac 上会自动签名。

### Python / CLI

```bash
pip install git+https://github.com/Hyunki6040/shortcut-forge
shortcut-forge template supplement-tracker --sign
shortcut-forge lint "My Shortcut.unsigned.shortcut"
```

```python
from shortcut_forge import Shortcut

sc = Shortcut("Hello")
name = sc.ask("你叫什么名字？")
sc.notify("你好", f"欢迎，{name}")
sc.storage_set("last_name", name)   # iOS 27 存储内容
sc.health_log("Vitamin D", "50")    # 自动 mcg → mg
sc.save("Hello.unsigned.shortcut")
```

## MCP 工具

`shortcut_build` · `shortcut_from_template` · `shortcut_lint` · `shortcut_inspect` · `shortcut_sign` · `shortcut_reference`

## 参与贡献

最有价值的贡献是**新的坑**：能导入但在真机上失败的快捷指令。请附上报错截图和最小复现 spec 提交 Issue，
我们会把它变成检查规则和构建器修复。

MIT 许可。与 Apple、Anthropic 无关。觉得有用请点个 ⭐。
