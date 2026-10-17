# Webbie Unified Workflow · Brain 2.0 + Eyes 2.0 + Hands 2.0 + Autopilot 2.0

October 11, 2026 · **SOURCE-ONLY DRAFT. NOT INSTALLED OR MERGED.**

This branch stacks after PR #88, PR #78, PR #76, PR #69, PR #68,
PR #67, PR #61, PR #54 and the guarded combined-release baseline.
It integrates EXISTING local focus, vision, computer control and task
receipts rather than replacing the more capable custom PC Webbie.

## User-visible experience

In The Web, select **Work with Webbie · guided workflow** or open it
from the Cognitive Control Center.

1. **Brain: choose existing Focus Task.** Use My Focus Tasks first to
   create an active task. Clicking Start takes that owner-created task.
   An LLM response, webpage, screenshot, incoming socket, or TV
   transcript cannot create or edit this task through the workflow.
2. **Eyes: consented screen inspection.** Clicking Open Computer
   Control merely opens the existing permission dialog. Select an
   installed application, describe/authorize a particular task, select
   and bind its exact window, click Inspect window once, and explicitly
   consent to one screenshot for the LOCAL Ollama vision model.
   The vision result is labelled untrusted and temporary. Raw image
   pixels are not stored in the workflow. Only a completed consented
   Computer Control screen-observation signal advances to action review.
3. **Hands: reviewed desktop operation.** In the existing Computer
   Control dialog review one installed app, browser, bounded navigation
   operation or bound window request. The new redacted Qt
   \`actionOutcome(action,outcome)\` signal connects its existing
   \`ActionReceipts\` to this workflow. No workflow button simulates
   keyboard/mouse or authorizes a grant. A command reported REQUESTED
   advances the checklist to verify; denied, failed, or window-observed
   alone cannot mark an operation complete.
4. **Autopilot: owner verifies real result.** The operator's launch,
   keypress or web-open request is NOT treated as proof the intended
   application state changed. The user checks the actual window and
   presses **I verified the result**, confirms an explicit dialog,
   or chooses Review again. The checklist stays in memory only.
   Up to **four separate reviewed cycles** may be completed, and each
   fresh step requires a new consented observation and reviewed
   operation. This is structured supervised automation, not autonomous
   inference or multi-application arbitrary task execution.

The dialog displays workspace, active owner task, current step,
consented-observation flag, redacted action class/outcome and the number
of owner-confirmed steps. Source CI tests the state machine and GUI.

## Security and privacy rules

* A single workflow expires after 30 minutes; changing workspace cancels.
* STOP, GUI close, sleep, desktop-authorization revocation, and parent
  Webbie panel close all cancel supervised progress.
* STOP and closing guided workflow revoke the existing computer grant,
  stop Webbie's camera and clear short-term screen awareness through
  the parent safety callback.
* No desktop permission extends beyond existing short-lived task grants.
* A task's private title is only displayed in the owner's GUI.
* The agent receives only a short-lived **phase-only** status such as
  "Unified workflow: verify" in the existing 90-second private
  GUI-to-agent context. It is labelled untrusted advisory information
  and cannot authorize OS, camera, app or network actions.
* Webbie can answer direct questions like "What is our workflow status?"
  from that expiring GUI context, rather than inventing progress.
* No audio, screenshot, raw task text, browser address, password,
  coordinates or voiceprint is written to a new long-term workflow log.
* Owner confirmation of one reviewed step does NOT mean the entire
  song, book, research job or repair is completed. Focus Tasks are
  not automatically marked done by these actions.
* The model may still hallucinate descriptions of an observed screen:
  the user must inspect the actual result before confirming success.

## Code changes

* \`webbie/brain/unified_workflow.py\`: deterministic single-workspace
  owner-guided state machine and four-stage/cycle limits.
* \`the-web/shell/webbie_unified_workflow.py\`: new purple Qt guided
  task dialog with legible stage/next-step/permission explanations.
* \`the-web/shell/webbie_computer_panel.py\`: redacted action outcome
  signal; existing grants, safe operator, observations retained.
* \`the-web/shell/webbie_panel.py\`: buttons and explicit trusted Qt
  integration; STOP, sleep, close cleanup; metadata publication.
* \`the-web/shell/webbie_cognitive_center.py\`: direct entry point.
* \`webbie/brain/context_awareness.py\`: normalize established The Web,
  Studio, Author and School workspace labels to the task board keys.
* \`webbie/brain/jarvis_context.py\`, \`webbie/agent/webbie.py\`:
  advisory-only expiring workflow phase and direct status questions.
* Guarded release manifests/audits and new backend/UI/context tests.

## Source regression

\`\`\`bash
python3 -m unittest discover -s tests -p test_webbie_unified_workflow.py -v
python3 -m unittest discover -s tests -p test_webbie_unified_workflow_gui.py -v
python3 -m unittest discover -s tests -p test_webbie_jarvis_context.py -v
python3 -m unittest discover -s tests -p test_webbie_cognitive_center.py -v
python3 tools/combined_release_audit.py --help
\`\`\`

GitHub automated tests validate SOURCE correctness only and cannot
prove the PC microphone, GPU/Ollama vision, Qt desktop focus, actual
application operation, or Cory/Shayna biometrics.

## Hardware/release blockers

The owner follows **one system-wide combined install per day**, with
hash-based reconciliation. Before installation, inspect the customized
running agent, face/eyes, microphone listener, TTS and speaker-security
stack. PR #76-#88 currently contain a strict voice identity gate without
a live validated Cory/Shayna offline biometric verifier, so
**do not install those stacked branches on the PC unchanged**. Such an
installation would block normal voice dialogue.

Reconcile all customized Studio, Author, Study, Kali Bay, Forage, Nova,
Media Center, Research, Web shell and shared models with staged source,
run live screen/permission/STOP/rollback tests, and preserve owner
documents and data. This branch makes no silent deployment changes,
new systemd services, cloud connections, model downloads, or repairs.
