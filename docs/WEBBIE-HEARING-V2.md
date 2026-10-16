# Webbie speaker-aware hearing v2

## Reason for change

Webbie's previous Whisper callback accepted any voice during a ten-second
follow-up window and recognized wake words inside unrelated words/sentences.
It used speech-to-text but **did not verify speaker identity**.

This change makes every *microphone* command require a match against an enrolled
voiceprint and binds the wake/follow-up window to that same person. Typed UI and
IPC commands are not changed.

## Intended authorized speakers

Cory and Shayna only. Profiles are **never** checked into the repo. They live
under `~/.config/spider-os/webbie/voiceprints.json` with owner-only permissions.
Raw WAV enrollment samples are removed after processing.

## Installation / dependency

This branch changes the Spider OS source tree. Updating GitHub by itself does
**not** update the installed `/usr/local/lib/spider-os` copy on the PC.

This uses `resemblyzer` for optional local CPU speaker embeddings. Before
deploying it on a PC, provide the dependency in the Python environment that
`webbie.service` runs. Prefer a dedicated venv to changing Ubuntu's system
Python. Do not force-install into an externally managed environment. Enrollment
and verification must use the same Python environment.

Then enroll in a quiet room:

```bash
python3 webbie/voice/speaker_guard.py status
python3 webbie/voice/speaker_guard.py enroll Cory
python3 webbie/voice/speaker_guard.py enroll Shayna
systemctl --user restart webbie.service
```

**Fail-closed:** If no voiceprints exist or `resemblyzer` cannot import, Webbie
ignores microphone commands. This prevents the unsafe fallback to accepting
any speaker. Confirm model availability and enrollment BEFORE activating the
branch's modified agent. For development only, `voice_access.require_voiceprint:
false` in Webbie config disables speaker checking (never use this for a
multi-person room).

Settings supported under `voice_access` in `webbie/config/default.json`
or a matching installed runtime config:

```json
{
  "voice_access": {
    "require_voiceprint": true,
    "threshold": 0.78,
    "min_gap": 0.06
  }
}
```

The defaults apply even without a `voice_access` section. The threshold is
a starting point, not a validated value. Test live with the actual microphone
and unwanted background speakers before trusting it.

## Tests

```bash
python3 -m py_compile webbie/agent/webbie.py webbie/voice/whisper_listener.py webbie/voice/speaker_guard.py
python3 -m unittest discover -s tests -p test_webbie_speaker_guard.py -v
```

Suggested real-world checks:

* Cory: `Hey Webbie, what time is it?` should be accepted.
* Shayna: same should be accepted.
* Unknown voice: same should be rejected.
* Cory: `Hey Webbie`, followed by a different speaker saying `open Firefox`,
  should be rejected.
* Cory: `Hey Webbie`, followed by Cory saying `open Firefox`, should work.
* Background `website` and casual conversation mentioning `web` should not wake Webbie.
* Replayed audio impersonating Cory or Shayna may fool the voice gate. For
  sensitive or destructive operations, use additional authentication/confirmation.

This change does **not** fix the user-facing barge-in problem during TTS.
Webbie already suppresses its mic during speaking, which also suppresses
`Webbie, stop`. Handle this as a separate, isolated upgrade.
