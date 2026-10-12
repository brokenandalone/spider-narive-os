# Webbie Jarvis: Resilience, Voice Metrics and Safer App Intent
## October 11, 2026 · Major SOURCE-ONLY upgrade

**No live PC installation, model change, account login, microphone recording
or restart was performed during this GitHub development round.**
This draft builds on PR #78 (Voice Lab), PR #76 (trusted voice/readiness),
PR #69 (cognitive focus), PR #68 (navigation), PR #67 (browser/context),
PR #61 (proactive), PR #54 (voice) and PR #49 (guarded combined base).
The owner's installed Webbie has additional custom enhancements and must
be reconciled before any combined release. This PR does not supersede them.

### 1. Local Ollama requests no longer block indefinitely by default

`webbie/brain/model_resilience.py` manages a PRIVATE, in-process
failure counter. The existing explicitly selected Ollama model remains the
only model used, on the existing localhost chat endpoint.

* Default chat request timeout is reduced from 180 seconds to 90 seconds.
* Owner may set `WEBBIE_OLLAMA_TIMEOUT_SECONDS` to an integer 10..180
  for a slower CPU, without modifying model settings.
* Model response JSON is bounded to 2 MB, rejecting malformed or empty
  results. No chat text is stored in the governor.
* Three consecutive request failures trigger a 45-second cooldown.
  This prevents many repeated 90-second timeouts when local Ollama
  is unavailable. A single half-open trial is allowed after cooldown.
* A successful reply clears the failure counter and resumes normal mode.
* The governor does not restart Ollama, alter Qwen/Gemma preferences,
  fetch models, call the cloud or assume the model is actually responsive.
* Model failures are answered with truthful temporary status, not a
  misleading generic chat and not persisted to recent conversation.

**Important:** A single 90-second HTTP timeout is not an actual
cancellable inference process. A physical PC review must confirm owner
hardware and choose an appropriate timeout before release.

### 2. Private, content-free Voice Lab counters

`webbie/agent/voice_metrics.py` adds a reset-on-service-restart
in-process counter for recognized text, unverified/rejected commands,
verified speech inputs, emergency STOP, queued corrections, and ignored
speech while Webbie is sleeping.

Only these numeric counters are added to the already owner-protected
`webbie.json` agent status; **no phrase, audio, speaker name, transcript,
screenshot, website or voiceprint is included.** Voice Lab displays
their interpretation, without claiming a biometric recognition score.
The readiness inspector reports when fresh counters are available.

These will be particularly useful for checking whether TV, visitors and
Webbie's own speech are being ignored. Counts alone cannot prove the
microphone works or distinguish which speaker made an attempt.

### 3. Safer, SHA-256-pinned offline voiceprint provider

`speaker_provider_loader.py` no longer accepts any same-named imported
Python package from `sys.path`. Enabling a local provider now requires
both `speaker_verification.enabled: true` **and** an exact lower-case
64-character `provider_sha256` pin to one locally installed audited
`webbie/voice/speaker_voice_provider.py` file. Missing, symlinked,
unexpectedly changed, world-writable, oversized or unpinned provider
code is rejected. Python compiles the exact approved file bytes
without reusing a module of the same name from the import cache.

The source default remains `enabled: false` and pin empty.
This does **not** bundle or create a speaker-biometric provider,
enroll Cory/Shayna, prove anti-spoof or make the existing PC accept voice.
The existing PR #76/#78 strict policy blocks ordinary microphone
dialogue until a real, owner-approved offline provider is integrated.
**Do not deploy this stack directly over the currently working PC.**

Voice Lab now distinguishes "provider file present" from "source hash
matches the owner's approved pin" and from "actual speaker verified."
The last of these is never claimed by read-only diagnostics.

### 4. No accidental application launching from casual speech

`webbie/agent/launch_intents.py` recognizes only complete direct
requests such as "Webbie, open Studio" or "please open Study." Legacy
launch handlers reject vague/negated/quoted commands such as:
* "Don't open terminal"
* "What happens if I open Kali Bay?"
* "Someone said open Studio"
* "Open terminal; run another command"

The parser is deterministic, not LLM-generated. Verified voice identity
and existing computer-control permissions are still independent.
This is a safety refinement, **not permission for autonomous PC control**.

### 5. One-click-source diagnostic CLI for staged rollout

From the GitHub source checkout, the owner may run:
```bash
python3 tools/webbie_readiness_cli.py
python3 tools/webbie_readiness_cli.py --json
python3 tools/webbie_readiness_cli.py --local-ollama
```
The default checks ONLY small owner-private status/config records and
presence of the microphone executable and model. The explicit
`--local-ollama` flag also contacts Ollama on 127.0.0.1 for installed
model tags, but sends no prompt. The JSON output is sanitized to coarse
statuses/counts and excludes model names, names of local files, window
content and transcripts. These checks do not repair problems.

### Source-only regression commands

```bash
python3 -m unittest discover -s tests -p test_webbie_model_resilience.py -v
python3 -m unittest discover -s tests -p test_webbie_voice_metrics.py -v
python3 -m unittest discover -s tests -p test_webbie_launch_intents.py -v
python3 -m unittest discover -s tests -p test_webbie_readiness_cli.py -v
python3 -m unittest discover -s tests -p test_webbie_segment_speaker_gate.py -v
python3 -m unittest discover -s tests -p test_webbie_voice_lab.py -v
python3 tools/combined_release_audit.py --help
```

All new runtime modules and the safe diagnostic CLI are listed in the
guarded one-install APP_FILES manifest and read-only source audit.
GitHub CI passing does not establish actual PC/camera/microphone or
biometric reliability.

### Blockers before one approved, reversible PC installation

1. Reconcile source hashes with owner's full existing Webbie, voice/TTS,
   face/webcam, live DJ/Nova, Author, Study, Studio, Kali Bay, Forage,
   Media Center, browser, KDE and account integration. Never overwrite
   unfamiliar customized files.
2. Review PC CPU/GPU/Whisper/Ollama performance, choose a timeout that
   works on installed hardware, test the circuit-breaker behavior.
3. Enroll and validate **a real owner-approved offline speaker verifier**
   for Cory/Shayna, calibrate acceptance/rejection using real household
   audio and TTS, test provenance/digest/liveness, and pin the source hash.
   If no verifier exists, hold the strict-voice gate from deployment.
4. Test negative app-launch commands, forced STOP, long responses, wake,
   sleep and the existing safety/grant UI. Test manual hearing only with
   explicit owner consent, and check complete temp-audio cleanup.
5. Preserve private conversation data, recordings, downloaded models,
   GPU settings, Nova radio and hardware setup; carry out a single
   guarded install with tested rollback only when safe.

**This PR is source staging, not a live Spider OS upgrade.**
