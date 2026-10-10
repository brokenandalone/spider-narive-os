# Webbie October 9–10 PC/GitHub compatibility ledger

Purpose: prevent a GitHub feature branch from downgrading the already installed
customized Webbie on Spider OS. This is a pre-installation release gate,
NOT a claim that a live PC was inspected through GitHub.

## Owner-confirmed and historical PC evidence

- October 9 installed PC comparison: approximately 2,300 lines of resident
  webbie.py and 850 lines of brain.py versus far shorter older GitHub agent
  and brain. Running PC has persistent conversation/history, memory recall,
  Forage/Firefox research and custom local speech/interrupt logic.
- Owner later confirmed the upgraded webcam works on the PC, including local
  camera descriptions and face overlay. It uses tested hardware capture
  settings; do NOT put the older default camera source back on that PC.
- Earlier local model inventory included qwen3:8b, qwen3:1.7b, gemma3:4b,
  and qwen3-vl:2b-instruct with local Ollama. Availability must be checked
  again; do not silently switch to GitHub's older 1.7B and Gemma fallback.
- Webbie/Webby wake aliases. "Webby stop" means STOP output/activity immediately
  but keep a 45-second multi-turn window for corrections. Explicit "That's all"
  means close dialogue, not kill wake-word listening. A sleeping face should
  close eyes, ignore ordinary speech but keep background jobs running.
  The latest portrait preference is lower-right, not earlier lower-left.
- Default authorized speakers ultimately Cory and Shayna; optional enrollment
  cannot block initial setup. Face matches, remembered names, transcription
  and screen content must never become command authentication.
- Shared assistant across all workspaces: Writer in Author, Justin in Studio,
  Spider in Kali, Student in Study. BCN Radio host calls herself Nova.
- Owner expects desktop app operation, original-voice music generation,
  Author chapter/book review/narration, Kali controls, Study school OneDrive,
  Media Center, and richer contextual intelligence. OneDrive is optional.
- Contextual awareness, memory, adaptation and humanlike interaction should
  mean real continuity, correction, task/state awareness, consented room/screen
  sensing, optional suggestions and honest uncertainty, not false claims
  of human consciousness, emotions, or capabilities.

## New source features in PR #47, stacked after PR #36

- Ephemeral context records per-workspace tasks, selection, user corrections,
  outcome verification and permission-labelled observations with short expiry.
  It does not replace the customized PC long-term memory.
- The Web panel provides an inspectable current context and hands off current
  authorized GUI task and fresh visual descriptions only under consent.
- Dialogue state keeps a multi-turn follow-up open after STOP but closes
  on a deliberate complete "That's all." Webby sleep/wake aliases supported.
- New local-model inventory uses only Ollama loopback /api/tags, respects
  explicit owner config and checks installed models. No pulls/switches.
- Supervised Autopilot from PR #36 remains task- and window-scoped and is
  not full unsupervised control.

## Concurrent GitHub PR overlap: integration required

- PR #30 touches webbie/brain/brain.py to preserve PC repairs. The shorter
  brain.py on older GitHub ancestors must not replace the PC memory engine.
- PR #37 (Author) changes webbie/agent/webbie.py,
  webbie/voice/whisper_listener.py and the-web/shell/webbie_panel.py.
  Preserve the added full-book reading, narration, and Author voice routes.
- PR #34 (Studio/Study) also changes webbie/agent/webbie.py and the
  release manifest. Preserve Studio and native school features.
- PRs #43 and #46 (Kali native Webbie controls) change the release
  manifest and Kali assistant code. Do not drop those install entries.
- PR #38 (BCN Nova) has been merged separately and must survive the eventual
  unified release; stacking #47 on #36 does not automatically include it.
- PR #31 (Webby alias) and #29 (camera 640x480 MJPEG) are on other stacks.
  Source work in #47 does not prove the working PC MJPEG patch was inherited.
- A green source PR, whether #36 or #47, is not a verified combined release.

## Mandatory live PC gate

From a checkout of the exact PR #47 head, as the normal Spider OS account,
run the following read-only source audit:

    python3 webbie/tools/installed_reconcile_audit.py --checkout "$PWD"

It prints SHA256 hashes, installed-only versus GitHub-only symbols and a
mandatory release hold. It never copies or edits the PC's installed code.
Inspect the current installed versions, not an old October 9 digest. Merge
changes only into a detached copy of those verified local files. Verify the
running camera model and 640x480 MJPEG, existing memory/research,
conversation/stop, Author narration, Studio, Kali, Nova, sleep/face and
OneDrive deferral. Validate the complete combined source and reversible
backup-first installer BEFORE any on-device installation.

STATUS: historical comparison and new source work done. Direct October 10
PC code inspection, cross-PR reconciliation, combined release installation
and device acceptance are still pending.
