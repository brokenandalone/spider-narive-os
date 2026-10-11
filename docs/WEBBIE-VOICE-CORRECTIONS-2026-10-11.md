# Webbie voice corrections: source-only upgrade (October 11, 2026)

**Status: DRAFT SOURCE. Do not install/merge to main or overwrite the
current customized Spider OS Webbie agent, brain, microphone listener, TTS or
camera files.** This branch is stacked on the October 10 combined draft release.

## Problem fixed in this source branch

The GitHub voice loop previously used a non-blocking worker lock. If the local
Qwen/Ollama model was still generating a reply, the next direct voice command
was silently thrown away. A user saying "Webbie, stop" could invalidate the
old reply yet still lose the correction spoken immediately after it. There was
also a TTS race: a late `speak()` call could clear a cancellation event and
start playback after STOP had been requested.

## Implementation

- `webbie/agent/voice_queue.py`: one model worker, one **latest** pending
  voice command. A subsequent correction replaces the previous pending turn.
  No audio recording, added model, identity claim or command privilege.
- Pending commands expire after at most 45 seconds, are rechecked against
  the live turn generation and sleep state, and disappear on STOP or "that's
  all". The wake recognizer remains active after "that's all".
- `webbie/agent/webbie.py`: uses the coordinator instead of ignoring busy
  voice commands, reports queued/started/ignored state, and invalidates voice
  work on STOP, sleep and explicit end.
- `webbie/voice/interruptible_speech.py`: locks playback's cancellation
  transition and checks that the originating voice generation is still valid
  before clearing a previous STOP. The stop handler terminates current
  playback if one exists.
- New no-hardware regression tests cover queued correction replacement,
  stop and recovery, expiry, sleep, fail-closed identity propagation, and
  stale-turn TTS suppression.

## Deliberate limitations

- Speech/model inference already running is not forcibly killed by this
  queue. STOP invalidates the reply and interrupts speech/consented GUI
  work; a pending corrected command runs only when the old worker yields,
  and only if it has not expired. No extra concurrent model workers are
  started. A future cancellation-aware Ollama client is still required for
  truly instant model-side cancellation.
- **Whisper transcription is not speaker verification.** The coordinator
  defaults `speaker_verified=False`. Source-only Author/Kali actions
  remain closed until a separately trusted Cory/Shayna verification adapter
  is connected and tested. Voice-driven app launch authorization must be
  audited on the actual PC.
- This does **not** prove USB webcam reliability, visual-model latency,
  exact Australian TTS voice, laptop microphone performance, face/sleep
  animation, Nova radio, KDE, or PC-specific Ollama performance.
- The on-PC Webbie agent is richer than the GitHub source. Do not copy this
  shorter agent onto the PC. Reconcile changes **into a detached copy** of
  current installed code, back up first, and use the single guarded release.
- Never use the webcam cord previously flagged for electrical overcurrent.

## Source checks and PC acceptance gate

Run repository tests (no camera/microphone/desktop effects):

```sh
python3 -m unittest discover -s tests -p 'test_webbie_voice_queue.py' -v
python3 -m unittest discover -s tests -p 'test_webbie_interruptible_speech.py' -v
python3 -m unittest discover -s tests -p 'test_webbie_voice_barge_in.py' -v
```

Before installing on Spider OS, compare fresh agent/brain/voice hashes and
current companion interfaces against the owner's latest PC build. Validate a
private staged package with the release audit and tests. When authorized by
those gates, verify *in person* on the real system:

1. Trigger a slow answer, then say "Webby stop" while Natasha is speaking.
   Spoken audio must cease; the old reply must not resume.
2. Say a corrected command within the next 45 seconds. It must not be
   silently discarded. If the first model worker is stuck too long, it must
   expire rather than executing later unexpectedly.
3. Say "that's all" and verify ordinary background speech cannot continue
   the conversation without wake. Sleep must ignore ordinary commands and
   close the face's eyes, while preserving unrelated background jobs.
4. Confirm screen/camera observation still requires explicit consent.
   Unverified microphone audio cannot open privileged Author/Kali actions.
5. Confirm native workspaces, Forage, Studio, Study/OneDrive, Nova/Media
   Center, active camera settings, and existing memory are untouched.

No installation or live PC audit is performed by this branch.
