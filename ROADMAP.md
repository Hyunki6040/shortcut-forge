# Roadmap: help wanted

The biggest unsolved problem in the Shortcuts ecosystem is not building shortcuts. It is **shipping updates**.
Today every fix means: rebuild → re-sign → re-share → every user re-downloads and taps "Replace". Settings are
often lost along the way. We felt this ourselves: the supplement tracker in `library/` went through six versions in
two days, and each one was a manual re-download.

Below is where we think this should go. Pick something, open an issue with your take, or send a PR.
Items marked 🧪 need people with real devices more than code.

## Now (v0.2, shipped)
- [x] `remote_config(url)`: data lives in a JSON URL, cached daily in Stored Content. Change the JSON and every
      installed copy picks it up tomorrow, no reinstall. (`library/lunch-picker-remote`)
- [x] `update_check(version, manifest)` + `shortcut-forge publish`: the shortcut checks a manifest once a day and
      offers to open the new signed file; iOS asks to replace it.
- [x] `shortcut-forge mac install-agent`: a launchd watch folder in iCloud Drive signs anything you drop in.
- [x] Community library with CI lint and per-entry `manifest.json`.

## Next: "Shortcut Hub" (central publish & update)
1. **One-command publish to GitHub** `shortcut-forge publish --github`: build, sign, upload to a GitHub Release,
   update `manifest.json` on Pages. Library entries get this for free on merge (macOS runner + a signing Mac relay).
2. **Stable install URL** `https://hyunki6040.github.io/shortcut-forge/s/<slug>` always serving the latest signed
   file, with a version history page and a changelog per entry.
3. **Settings survive updates.** Generated shortcuts keep user state in Stored Content (never in the action list),
   so replacing the shortcut keeps your env. Formalise it: a `schema` key + migrations, like we did by hand
   (`storage_wipe` + schema bump).
4. **Loader pattern (experimental).** A tiny, rarely-changing "loader" shortcut fetches a JSON program from the Hub
   and dispatches to a set of generic building blocks. Most behaviour changes become a JSON change. Trade-offs:
   network dependency, Shortcuts' lack of try/catch, App Review-style trust questions. Needs prototyping 🧪.
5. **Update UX research** 🧪: does opening a signed `.shortcut` URL on iOS 27 reliably show "Replace existing"?
   Does it keep the icon, automations, home-screen placement? We need reports from many devices.
6. **Signing relay.** Signing needs a Mac with an Apple ID. A self-hostable relay (`shortcut-forge relay`) so a
   team's single Mac signs for everyone, plus a GitHub Action that calls it for library PRs.

## Builder & linter
- More verified actions: Messages, Notes, Photos, Focus, HomeKit, Files, Music 🧪 (send a device report and we flip
  "modelled" to "verified")
- Import an exported shortcut → JSON spec (round-trip), so people can refactor existing shortcuts with an AI
- Rule packs: "automation-safe" (no prompts), "watchOS-safe", "Mac-safe"
- A visual diff of two versions of a shortcut for PR review

## Ecosystem
- Submit to the official MCP Registry and Anthropic's connector directory (in progress)
- Codex / ChatGPT / Gemini walkthrough videos
- Localised READMEs and library descriptions (ja, zh, es, de… PRs welcome)

---

## 한국어 요약

단축어 생태계의 가장 큰 미해결 문제는 만드는 게 아니라 **업데이트 배포**입니다. 지금은 수정할 때마다 다시
빌드하고, 서명하고, 공유하고, 모든 사용자가 다시 내려받아 "대치"를 눌러야 합니다. 설정이 날아가기도 하고요.
이 저장소의 영양제 단축어도 이틀 동안 여섯 번을 그렇게 다시 받았습니다.

- **지금(v0.2):** 데이터는 JSON URL로 분리(`remote_config`, 하루 한 번 캐시) → 재설치 없이 반영. 코드 변경은
  `update_check` + `publish`로 단축어가 스스로 새 버전을 안내. iCloud Drive 감시 폴더가 자동 서명.
- **다음, "Shortcut Hub":** 한 줄 명령으로 GitHub 릴리스 배포, 항상 최신을 주는 고정 설치 URL, 업데이트해도
  설정이 유지되는 스키마/마이그레이션, JSON 프로그램을 받아 실행하는 로더 패턴(실험), 팀용 서명 릴레이.
- **도움이 필요한 곳:** 실기기 검증 리포트, 업데이트 UX 조사(iOS 27에서 "대치"가 아이콘·자동화를 유지하는지),
  새 동작 검증, 다국어.
