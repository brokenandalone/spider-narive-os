# Spider OS Wave Four | JARVIS Local Workflow Board & Resilience

**Status: Draft source integration. No live PC installation or service restart.**
Stacking: Wave Two #81 → Wave Three #87 → Wave Four #92.
All PC source changes remain guarded by the single owner-approved daily install.

## What is actually built

**JARVIS Workflow Board:** `webbie/agent/workflow_board.py` defines five reviewed,
non-executable cross-workspace plans. The native Qt dialog in
`the-web/shell/webbie_workflow_dialog.py` is linked from the existing
Webbie Cognitive Center. Templates include recording, coursework, Broken World
canon, BCN broadcasting preparation, and system maintenance. The owner must:
1. Select a known workflow in the GUI.
2. Click Start and accept the visible confirmation prompt.
3. Click to open one fixed native workspace. This is only a workspace
   navigation request, NOT a generic program launch or a claim of success.
4. Review external results and click to mark that specific step complete.
5. Explicitly stop the plan or let its bounded timer expire.

No arbitrary shell, generated commands, keyboard presses, websites,
photographs, files, audio, model instructions, broadcast starts or backups are
performed by this workflow board. It does not read personal project content or
save a history. Clicking STOP clears the current checklist, but desktop grants
have a separate emergency STOP action, clearly disclosed in the interface.

**Direct typed JARVIS requests:** The Web's own Webbie chat box recognizes
complete literal phrases such as `Webbie, prepare my recording session`,
`Webbie, prepare my coursework`, `Webbie, review Broken World continuity`,
`Webbie, prepare BCN broadcasting`, and `Webbie, check Spider OS readiness`.
These phrases only open the relevant Workflow Board *preview*. A direct GUI
owner confirmation is still required to start it, and each fixed workspace
is only opened by another explicit button click. No voice transcript, AI
reply, copied webpage content or camera observation can authorize this route.

**Webbie resilience:** Carefully scoped patches from PR #88 add a local
model-request circuit breaker; private process-local voice intake counters with
no transcripts or voiceprints; strict literal launch-intent parser; an opt-in,
pinned-source offline speaker verifier loader; and a read-only readiness
command `tools/webbie_readiness_cli.py`. No cloud model fallback, automatic
model download, voice enrollment, camera capture, or service restart.

**Connected UI:** The Web supplies the workflow navigation callback only to the
Webbie Qt panel. The resident AI agent never receives the callback and cannot
use a language-model answer, remote website, camera text, or spoken sentence to
start the GUI workflow. Existing Webbie verified-speaker and desktop task grant
checks remain separate and enforced.

**Install and integrity:** The modules are explicitly added to
`system/release_batch.py`'s `APP_FILES`. The read-only
`tools/daily_pc_acceptance.py` includes them as exact planned new files:
missing planned modules are allowed only *before* the first reviewed install,
and missing modules *after* installation block acceptance. Customized existing
installed code and symlinked paths remain blocked. The once-daily crash-safe
installation policy from Wave Three is retained, as is unrestricted rollback.

## Review and test protocol

- `python3 -m unittest discover -s tests -p 'test_*.py'` on the **exact**
  Wave Four SHA.
- Review GitHub Actions jobs and offscreen desktop smoke on the same SHA.
- `python3 tools/daily_release_continuity.py --json` should remain **BLOCKED**
  until actual installed PC differences, branch overlaps, backup recovery,
  owner approval, and single local daily installation slot have been verified.
- On the actual PC, run `python3 tools/daily_pc_acceptance.py --phase before --json`
  from the staged checkout. It does not install anything, access private
  schoolwork/manuscripts, or restart services.
- After one approved installation, run `--phase after --json` and check Webbie
  hearing/STOP/authorized speakers, models, active-window permission, all GUI
  workspaces, Nova audio, Study/Author/Studio data, Kali Bay and recovery.
- Source code and CI **cannot** prove the real PC microphone, GPU, speaker
  identity, screenshot permission, shell usability, audio output or boot safety.

No merge to a deployable branch or on-PC install is authorized by this PR.
