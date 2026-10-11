# Webbie Jarvis Voice Lab & Segment Verification
## Major source upgrade · October 11, 2026

**DRAFT SOURCE ONLY. NOT MERGED OR INSTALLED ON OWNER'S CUSTOM SPIDER OS PC.**
Stacked after trust/readiness/receipts PR #76, cognitive PR #69, missions
PR #68, browser/context PR #67, proactive PR #61, voice PR #54 and the
guarded combined-release baseline. The installed resident voice agent is
customized and cannot be safely replaced wholesale from the repository.

### Voice pipeline: audio-segment trust rather than a claimed speaker

The existing Whisper listener records short WAV chunks and transcribes them.
This branch adds an OPTIONAL `verifier` callback that receives the **same**
WAV before the existing loop removes it. A new, owner-audited offline
provider must return a `SpeakerEvidence` for Cory or Shayna with:
* literal `verified=True`, exact trusted verifier provenance and age <=30s
* a SHA-256 digest matching the exact short WAV segment, no changed audio
* finite confidence >=0.88 and <=1.0, provisionally; calibrate against
  real users and false acceptance on the PC before any deployment

Neither Whisper transcript text, a claimed name, wake phrase, face
similarity, language-model reasoning, nor an untrusted shell response
passes as voice authentication. The direct request and single-worker
queue now carry evidence to the resident handler. **Emergency STOP
continues to work from any recognized speaker.** Everything else,
including wake, sleep, greetings, and follow-up speech, remains blocked
without verified audio. Typed GUI requests remain separately available.

The provider loader is opt-in through the new configuration entry:
```json
"speaker_verification": { "enabled": false }
```
Only a separately installed, owner-audited
`webbie/voice/speaker_voice_provider.py` module exposing
`verify_audio_segment(wav_path)` may be loaded when the user explicitly
enables this feature. It is **NOT INCLUDED** and is NEVER downloaded,
invented, enrolled, or activated by this PR. The 0.88 score is a
source-stage minimum, **not** validated biometric performance.
Do not assume the standalone evidence data class is a cryptographic
identity mechanism; the real offline model, anti-replay/liveness controls,
enrollment, thresholds and owner-specific false-acceptance testing remain
to be designed and validated. Default failure is silence, not guessing.

Even without a provider, Whisper still captures brief chunks to recognize
STOP, which must be documented to the owner. Audio is not disabled.
If the user wants the microphone completely off, stop the voice listener
using existing OS controls; this PR makes no such change itself.

### Visual Listening status

A new owner-runtime `webbie-listening` marker is created only while
the actual `arecord` subprocess attempts capture, then removed
immediately. The Web's portrait can show **Listening through the
configured microphone** rather than just **Webbie service detected**.
The marker is ignored if symlinked/stale/not owner-owned; it never
authenticates speakers or grants commands. TTS speaking state takes
precedence. Nothing from an audio recording is put in the marker.

### Voice Lab in Jarvis Cognitive Control Center

The new **Voice Lab diagnostics** button checks only whether:
* local Whisper executable is present,
* the existing language model is present,
* ALSA `arecord` utility is present,
* local speaker verifier config has been explicitly enabled and a
  potential provider file exists.

These are presence checks only: no model downloads, recordings,
microphone opening, service restart, cloud call, voiceprint enrollment
or unreviewed change. No claim of "working microphone" or "identified
Cory/Shayna" follows from this report.

### Optional manual three-second hearing test

The **Test Webbie hearing (3 sec)** button starts only after a
QMessageBox owner confirmation and runs a bounded local recording
and Whisper transcription on a Qt worker. It requires an owner-private
`XDG_RUNTIME_DIR/spider-os` directory. A temporary 0700 subdirectory
holds the three-second WAV and short result until the test ends, then
both are deleted, including timeout/normal-error paths. No transcript
goes into Webbie's persistent memory, the task board, proactive checks
or connected services. The brief transcript is displayed only in the
local test window. If Whisper or the recording device is missing,
occupied by the resident voice listener, or times out, the UI shows a
clear result. No microphone is tested by this GitHub pull request.
On an actual Linux install, confirm runtime directory is on a private
tmpfs; this test refuses world-readable directories. SIGKILL/power
failure behavior and local storage security require separate PC testing.
A hearing test cannot prove who spoke or grant command authorization.

### Regression checks

```bash
python3 -m unittest discover -s tests -p test_webbie_segment_speaker_gate.py -v
python3 -m unittest discover -s tests -p test_webbie_whisper_segments.py -v
python3 -m unittest discover -s tests -p test_webbie_voice_lab.py -v
python3 -m unittest discover -s tests -p test_webbie_hearing_test.py -v
python3 -m unittest discover -s tests -p test_webbie_listening_indicator.py -v
python3 -m unittest discover -s tests -p test_webbie_cognitive_center.py -v
python3 tools/combined_release_audit.py --help
```

All source modules are in `system/release_batch.py` APP_FILES and in
the read-only `tools/combined_release_audit.py`. Existing voice
conversation, model, Study, Author, Studio and desktop safety tests
must remain green.

### Strict once-per-day installation hold

1. First reconcile and back up the **actual installed customized agent**
   and microphone setup against all stacked source PRs.
2. Verify owner-private runtime filesystem, Whisper version, speaker
   model dependencies and actual microphone capability without disrupting
   Webbie's running audio or Nova/BCN live broadcasting.
3. Do not enable speaker verification until a separate verified speaker
   model is locally installed, owner voices are explicitly enrolled,
   and true/false matches, wake, sleep, STOP and TTS echo are tested
   with Cory, Shayna and common room/TV voices.
4. Conduct explicit owner-click manual hearing test, voice status,
   and downgrade/rollback drills. Leave default opt-in OFF if no model
   is available. A default-disabled verifier means ordinary voice is
   blocked by the already staged PR #76 policy, so **PR #76 and this
   PR must NOT be shipped without resolving that mismatch**.
5. Merge/stage as ONE coordinated, reversible installation only after
   installed-PC hashes, regression suite and owner's approval. No service
   or webcam USB repair is attempted by these source commits.

**No real audio, speaker enrollment, deployment, installer, or physical
PC controls were accessed while building this branch.**
