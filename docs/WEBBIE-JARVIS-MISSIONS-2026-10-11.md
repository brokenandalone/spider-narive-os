# Webbie Jarvis navigation missions & action transparency
## Major source-only upgrade · 2026-10-11

**STATUS: STAGED ON GITHUB, NOT INSTALLED ON THE CURRENT SPIDER OS PC.**

This feature branch builds directly on Jarvis contextual website control PR #67,
which builds on proactive checks PR #61 and voice interruption PR #54. Keep the
one-batch release dependency order and do not install the shorter repository
agent over the owner's more capable customized desktop Webbie.

### 1. Supervised natural-language navigation missions

Direct, owner-typed commands like these now open the existing trusted
Computer Control panel with a **preview**:

- `scroll down twice`
- `page up three times`
- `next tab then go back`
- `go forward and then reload page`
- `Webbie, scroll down 2 times then go back`

Commands are parsed deterministically, not by an LLM. Only static
window-confined keys are allowed: Page_Up, Page_Down, alt+Left, alt+Right,
ctrl+r, ctrl+Page_Up and ctrl+Page_Down.

Missions are limited to **six reviewed steps**, **two minutes**, **one
specifically bound window**, and one **already approved local desktop task**.
Browser-only commands require an installed browser selected in the existing
XDG application picker. Every step requires a **new click** on Run Next
Reviewed Step. No scrolling, tab switch, navigation, app launch, or keystroke
runs from the preview itself. Changing the window/app, STOP, grant expiration,
or a failed step discards remaining steps. No retries or model-suggested
mouse positions are introduced.

### 2. Spoken navigation staging, not unauthorized actuation

The resident voice handler can recognize the same phrases and send a
`PLAN:<text>` request to the local operator panel **only while an owner-granted
task already has that bridge open**. The bridge *stages text only* and does
not send keyboard commands. The GUI still requires bound-window review and
per-step clicks. Without the panel/grant it tells the owner what to open.
No speaker-identity claim is made from a Whisper transcript or camera face
cue. Cory and Shayna's separately trusted microphone speaker verifier is a
later PC-specific prerequisite for hands-free actuation.

### 3. A private Jarvis activity timeline

The Computer Control panel now shows the current session's latest thirty
**redacted event types** including authorization, website open requested,
mission staged, reviewed step, mission completed/canceled, window chosen,
one-window snapshot, and STOP. It logs no URLs, passwords, page content,
typing, screenshots, document titles, coordinates, text, audio or remote
telemetry. The owner can click Clear History, and it is not written to disk.

### 4. Context understands mission progress

During an active desktop grant, The Web may publish a bounded, short-lived
mission progress label, such as `Step 2 of 3: Go Back`, together with the
existing approved task and selected window. This advisory-only state expires
in 90 seconds; it is cleared on sleep and cannot authorize tools or mutate
long-term memory. Webbie can answer `What step are we on?` or `What is the
next step?` from this limited GUI-reported status. Actual screenshot
analysis still needs explicit owner consent and local vision.

### 5. Studio and Media Center launcher repairs

The previous GitHub resident agent responded to `open Studio` by only
changing the selected workspace; it still tried a legacy Media Player name
when opening Media. The upgraded source resolves *fixed, local and present*
Spider Studio entrypoints, and prefers the installed Spider Media Center
launcher over the older Spider Media Player fallback. Missing launchers
cause an accurate failure response instead of falsely claiming successful
launches. No arbitrary shell execution or LLM-provided launch path.

### Source checks / acceptance

```bash
python3 -m unittest discover -s tests -p test_webbie_navigation_missions.py -v
python3 -m unittest discover -s tests -p test_webbie_navigation_gui.py -v
python3 -m unittest discover -s tests -p test_webbie_action_journal.py -v
python3 -m unittest discover -s tests -p test_webbie_workspace_launchers.py -v
python3 -m unittest discover -s tests -p test_webbie_jarvis_context.py -v
python3 tools/combined_release_audit.py --help
```

The one-batch `system/release_batch.py` APP_FILES list and combined release
audit include every new module. Green GitHub CI confirms only source-level
behavior; it cannot verify your installed microphone, webcam, monitor,
window geometry, selected actual browser, installed Studio launcher, models,
custom memory, full desktop workflow, or real keyboard behavior.

### Mandatory one-install-per-day PC reconciliation gates

- Back up and hash the actual current PC agent, brain, voice, model choices,
  camera and shell before applying *any* upgrades.
- Compare current source and review differences against staged PRs #49,
  #54, #61, #67 and this PR. Avoid duplicate classes, conflicting imports,
  orphaned services, and overwriting the more advanced customized PC agent.
- Run lint/import, native Qt offscreen checks and all previously passed
  source/regression suites in a separate staging directory.
- On the actual machine, check owner grant, exact-bound X11 window selection,
  selected browser, desktop STOP semantics and one-step mission execution,
  never on sensitive/password/financial windows.
- Smoke test Studio, Media Center/Nova, The Web, Forage/Deep Forage, Study,
  Author, Kali Bay, proactive checks, reminders, recovery/memory and the
  webcam with a *safe* cable only. Never stress the earlier overcurrent
  webcam connection.
- Don't install, replace or restart live components while the native
  reconciliation is blocked; preserve reversible backups and restore plan.

**Not merged, not installed, no live PC acceptance test has happened.**
