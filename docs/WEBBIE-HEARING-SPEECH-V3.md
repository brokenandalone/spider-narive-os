# Webbie Hearing + Speech v3 (October 2026)

This branch extends Hearing v2 without overwriting its local voice authorization.
No code is installed on the user's PC by merging a PR.

## Hearing
- Offline WAV audio-activity gate skips many silent/noisy 4-second recordings before calling Whisper; it is NOT speech classification.
- Normalize known hallucinations and drop identical consecutive transcripts within a short window.
- Retain voice verification for Cory and Shayna on **every** utterance.
- Wake words must start a phrase; the ambiguous 'web' alone cannot wake Webbie.
- During speech, microphone capture is 2 seconds when barge-in is enabled; only verified explicit phrases like **"Webbie, stop"** can interrupt her. Webbie never executes an unrelated command heard during TTS.
- Echo and music can still interfere; microphone echo cancellation is hardware-specific and not included. Replayed authorized voices may fool speaker verification.

## Speech
- Use interruptible subprocesses for Edge/Natasha TTS and offline espeak-ng fallback.
- Spoken version of long markdown/text is trimmed and code blocks/URLs are not read aloud verbatim.
- The user-facing reply remains intact in Webbie state; spoken text can be shorter.
- A rolling in-memory conversation history (4 short turns) follows up within the *same* authorized voice or typed session. History is not persisted to disk.
- Voice response can be stopped from text/IPC with `stop` even if the microphone is not active.

## Dependencies and compatibility
- Defaults rely on standard Python for audio and TTS control, and on preexisting `whisper-cli`, `arecord`, Edge TTS or espeak-ng.
- Hearing v2 **still requires** `resemblyzer` and locally enrolled authorized profiles for microphone commands. Missing voiceprints or model means microphone control fails closed, not open.
- WAV activity is a fast energy gate, not a guarantee of reduced false transcription.
- Barage-in listens while Webbie is playing speech, which may consume extra CPU and permit speaker-output echo into capture. Set `WEBBIE_ALLOW_BARGE_IN=0` in the user service environment to preserve the old behavior if necessary.
- On a PC whose installed Webbie differs from this GitHub revision, do not overwrite installed files wholesale: compare and back up before merging into the daily install batch.

## Tests
```bash
python3 -m py_compile webbie/voice/speaker_guard.py webbie/voice/audio_gate.py webbie/voice/tts.py webbie/agent/webbie.py webbie/voice/whisper_listener.py webbie/brain/brain.py
python3 -m unittest discover -s tests -p test_webbie_speaker_guard.py -v
python3 -m unittest discover -s tests -p test_webbie_hearing_speech_v3.py -v
```

## Hardware checklist (not yet validated remotely)
1. Cory says: `Hey Webbie, what time is it?`
2. Shayna says it, then an unrecognized speaker says it.
3. Cory says `Hey Webbie`; another voice tries a follow-up instruction.
4. Cory starts a long answer, then says `Webbie, stop` **while she is talking**.
5. Ask `What is Spider OS?`, then `What was I asking about?` and confirm context.
6. Play TV audio near the webcam while Webbie is replying. Confirm no accidental actions.
7. Interrupt by typed/IPC `stop` even when TTS is using the offline fallback.
8. Test in the actual 60% webcam gain environment; calibrate the voice threshold only after authorized/unauthorized trials.

## Installation decision
Don't deploy v3 onto the PC until the previous Hearing v2 gate has been enrolled and the installed agent compared. GitHub CI tests are simulations, not evidence of real microphone success.
