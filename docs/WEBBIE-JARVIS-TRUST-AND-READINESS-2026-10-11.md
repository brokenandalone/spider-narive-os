# Webbie Jarvis: Trust, Readiness and Action Receipts
## October 11, 2026 · Source-only upgrade

**This branch is not installed.** The user's PC has a customized Webbie
installation that must be hashed and reconciled before a single coordinated
installation. This PR stacks on #69, which itself stacks on #68, #67, #61,
#54 and the guarded combined release base. No PC services, USB cameras,
Whisper samples, passwords, schoolwork, memories, models or system files
were touched while creating this GitHub source update.

### Trust boundary: only two approved voice users

The owner previously specified that Cory and Shayna should be the **only**
authorized voices. The existing source recognized some sensitive commands
as verified but still processed ordinary microphone transcripts. The new
`voice_trust.py` introduces a fail-closed check:

* Fresh, explicit evidence is required from an independently authenticated,
  locally trusted voice-verification adapter.
* The requested name must be Cory or Shayna, verified must be literal True,
  provenance must be `trusted.local_speaker_verifier`, and evidence must not
  be over 30 seconds old or issued in the future.
* A mere `speaker_verified=True` boolean, spoken name, wake word, Whisper
  transcript, webpage instruction, LLM answer, or camera face match is **not
  evidence**.
* Unverified microphone input is ignored without saving overheard words
  to Webbie's chat/status. STOP remains universally available as an
  emergency intervention.
* Direct typed requests to the on-device GUI remain a distinct path.
* **There is no connected real voice verifier in this PR.** Accordingly, on
  an unmodified installation of this code, ordinary microphone dialogue
  will NOT operate until a real, owner-consented verifier is tested. Do not
  deploy this voice gate to the actual PC ahead of verification: preserve
  existing customized PC audio with staged, reversible integration testing.

This gate is a trust policy, not a speaker-recognition algorithm and not a
cryptographic identity token. It must not be satisfied by manually
constructing fake evidence based on a person's claimed name.

### Runtime readiness without self-repair side effects

`webbie/agent/runtime_readiness.py` reads only small owner-private
status records. It reports:

* Whether a recent resident Webbie heartbeat was **reported** (not proof
  the current PC voice or chat is functional).
* Whether the resident microphone listener reported active or failed.
* Whether the ephemeral trusted-GUI workspace context is fresh.
* Whether existing proactive checks have saved readable results.
* Whether Webbie's private-session memory setting is active.
* Whether a trusted speaker-verifier integration is missing.

None of these checks opens a microphone/camera, lists private documents,
downloads a model, restarts systemd, accesses the cloud, or mutates the OS.
Readiness is now visible through an **Inspect Webbie readiness** control in
the Cognitive Control Center and through direct read-only typed commands
such as `diagnose Webbie` or `what is working right now`.

The existing proactive monitoring continues independently. User's real PC
has its own older `webbie-proactive.timer` and a failed
`webbie-research.service` record: this source change does **not** claim
either is repaired or that the user's current service state was inspected.

### Truthful desktop action receipts

New `webbie/actions/action_receipts.py` and the Computer Control panel
make a strict distinction between:

* **Requested:** a browser launch request or keyboard operation was
  dispatched; destination contents/task completion are not verified.
* **Denied:** authorization missing or declined.
* **Failed:** the target action returned failure.
* **Observed:** an authorized window/sample interaction was reported.
* **Canceled:** owner STOP or cancel revoked action.

Receipts contain one allowlisted action category + outcome, not URLs,
titles, prompts, file paths, keyboard content, coordinates, screenshots,
or names. They expire after 90 seconds, are memory-only in the GUI, and
are never persisted as a separate log. A short advisory-only receipt flows
into the existing private GUI-to-agent context, so the assistant can answer
`What did you just do?` without falsely claiming the page loaded.
The context is temporary, does not approve new computer actions, and is
cleared on sleep. Existing session-local redacted activity history remains
available and clearable.

### Test commands

```bash
python3 -m unittest discover -s tests -p test_webbie_voice_trust.py -v
python3 -m unittest discover -s tests -p test_webbie_runtime_readiness.py -v
python3 -m unittest discover -s tests -p test_webbie_action_receipts.py -v
python3 -m unittest discover -s tests -p test_webbie_action_receipts_gui.py -v
python3 -m unittest discover -s tests -p test_webbie_jarvis_context.py -v
python3 tools/combined_release_audit.py --help
```

All new modules are included in `system/release_batch.py` APP_FILES and
`tools/combined_release_audit.py` read-only component/wiring checks.
GitHub test runner success is SOURCE verification, **not** live PC
microphone, KDE, X11, camera, Ollama, or speaker-verifier acceptance.

### Next acceptance gates before the once-daily combined PC install

1. Hash and preserve the installed agent, Whisper listener, Natasha TTS,
   custom face/camera, brain/memories, Studio, Media Center/Nova, Study,
   Author, Forage/Deep Forage, Kali Bay, The Web and all user config.
2. Determine what trusted owner voice authentication hardware/software
   actually exists. If unavailable, hold the voice policy separately or
   keep a compatibility gate that preserves the original PC voice behavior
   until the owner explicitly approves a change.
3. Reconcile all stacked draft PRs in an isolated staging tree, run syntax,
   source, Qt and current-PC-specific tests. No unsupported hot patching.
4. Verify genuinely working stop, interrupt, conversation, original awake
   portrait, filled closed eyelids in sleep, context expiry, accurate
   action receipts and browser load-not-confirmed semantics.
5. Verify unrelated workspaces and Nova radio status did not regress.
   Source CI cannot establish real broadcast on-air availability.
6. Only then perform one owner-approved guarded installation with rollback.
   Do not touch the previously flagged unsafe webcam USB cord.

**No merge, release or installation action is included in this update.**
