# 📚 The Open Shortcut Library: share what you built

> **Built a shortcut with Claude, Codex or ChatGPT that you actually use? Put it here.**
> Every entry is a reviewable JSON spec (not an opaque binary), lint-checked in CI, and signed by a maintainer
> on a Mac so anyone can tap it on their iPhone. 한국어 안내는 아래에 있습니다.

**Browse:** [library/INDEX.md](library/INDEX.md) · or ask your AI: *"show me the shortcut-forge library for reminders"*
(MCP tool `shortcut_library`).

## Why share here instead of an iCloud link?

| iCloud link / RoutineHub file | Open Shortcut Library |
|---|---|
| Opaque. You can't review what it does before installing | Plain JSON spec you can read and diff in a PR |
| Fixing a bug = new link, everyone re-downloads by hand | Version + `manifest.json`; shortcuts built with `update_check` offer the update themselves |
| Breaks silently on new iOS versions | CI re-lints every entry against the 15 on-device rules on every change |
| Hard to remix | `shortcut_library(slug=…)` hands the spec to your AI as a starting point |

## Submit in 3 minutes (the AI does most of it)

1. **Build it** with any MCP client: *"Make a shortcut that …"*
2. **Run it on your iPhone** for a few days. Note your device and iOS version.
3. Tell your AI: **"Submit this to the shortcut-forge library."** It calls `shortcut_submit`, validates the
   metadata, lints the spec and gives you the exact files and commands:

```bash
gh repo fork Hyunki6040/shortcut-forge --clone && cd shortcut-forge
shortcut-forge library add my-shortcut --spec my_spec.json \
  --name "My Shortcut" --description "What it does in one line" --category productivity --author <github-handle>
shortcut-forge library check
git checkout -b library/my-shortcut && git add library/my-shortcut && git commit -m "library: add my-shortcut"
gh pr create --fill --label library
```

No terminal? Open an issue with the JSON spec pasted in. A maintainer will add it.

### What makes a great entry
- Solves one real annoyance (the best ones start with *"I was tired of…"*)
- `verified_on` filled in (e.g. `iPhone 15 Pro, iOS 27.0.1`)
- No secrets, no personal data. Ask for tokens on first run and keep them in Stored Content
- `description_ko` welcome (any extra language is)
- Data that changes often → `remote_config` JSON, so it updates without reinstalling

### Categories
`productivity` · `health` · `wellbeing` · `money` · `home` · `travel` · `language` · `developer` · `automation` ·
`team` · `morning` · `starter` (propose new ones in your PR)

---

## 한국어: 내가 만든 단축어를 공유해 주세요

Claude·Codex·ChatGPT로 만든 단축어 중 **실제로 매일 쓰는 게 있다면** 여기에 올려 주세요. 모든 항목은
리뷰 가능한 JSON 스펙으로 올라가고, CI가 15개 실기기 규칙으로 검사하며, 메인테이너가 Mac에서 서명해
누구나 아이폰에서 탭 한 번으로 추가할 수 있습니다.

**제출 방법:** MCP로 만든 뒤 AI에게 *"이거 shortcut-forge 라이브러리에 제출해줘"* 라고 하면 `shortcut_submit`이
메타데이터 검증, 린트, PR 명령어까지 준비해 줍니다. 터미널이 어렵다면 이슈에 JSON만 붙여 주세요.

**좋은 항목의 조건:** 실제 불편 하나를 해결할 것, 실기기 검증 정보(`verified_on`), 비밀값·개인정보 없음,
자주 바뀌는 데이터는 `remote_config` JSON으로 분리(재설치 없이 업데이트).
