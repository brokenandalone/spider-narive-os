# Author Bay: full reviews and Webbie narration

## What the new controls do (source stage, not installed-PC acceptance)

- **Webbie: Review entire chapter** reviews every nonempty portion of the currently selected chapter.
- **Webbie: Review entire book** reviews every nonempty portion of every chapter of the selected book, in order.
- **Quick review** uses larger bounded segments and shorter responses; **Deep review** uses smaller segments and more detailed responses. Even quick mode processes all content. Neither claims instantaneous results on CPU hardware.
- A private content-hash cache keeps review observations for unchanged segments so repeat reviews reuse local results instead of regenerating them. Changed text, model and response settings invalidate the corresponding entries. The raw manuscript is not stored in the cache, but review observations themselves can contain sensitive details and are stored in a user-private 0600 SQLite file under the local XDG cache directory.
- Each segment receives a local Ollama analysis using Webbie's configured model (`webbie/config/default.json`, fallback `qwen3:1.7b`). The text remains on the user's machine at `127.0.0.1:11434`. No public LLM API or automatic OneDrive transfer is used.
- A progress label, cancellation button, chapter/segment findings and bounded overall synthesis appear in Author's Writing Studio. No automatic manuscript edits are made.
- **Webbie: Read current chapter** and **Webbie: Read entire book** reuse the same installed `webbie/voice/tts.py` as the resident assistant. That voice currently prefers Natasha online with Webbie's established offline fallback. The generic Author eSpeak voice is no longer the default reader for these controls.
- Stop terminates the current voice subprocess group, including playback children. Pause takes effect after the current spoken section; resume continues in order. No auto-reading or auto-review runs on open.

## Limitations and follow-up gates

- The new commands are **Writing Studio buttons** and explicit typed instructions in The Web's Author Webbie chat panel. These route through an owner-local UNIX socket, rather than pasting the whole book into an LLM prompt. Only the selected book/chapter is accessed, and no automatic review starts.
- A **fail-closed spoken-command hook** is prepared in Webbie's source. It refuses Author actions unless a separately verified authorized speaker identity is supplied. The baseline Whisper listener has no qualified speaker-verification result, so spoken Author commands are **not yet enabled** until the customized PC voice-gate is reconciled and tested. Never treat ASR text or face recognition as speaker authentication.
- The book review model is not omniscient: it analyzes bounded segments and synthesizes its own observations. It can miss cross-chapter contradictions or make mistakes. Reports identify segments to revisit.
- Book review calls may take substantial time depending on model and PC speed. There is no full-book one-prompt context window or hidden skipping to create a fake instant result.
- The current narrator invokes the established Webbie voice module per section rather than controlling the resident Webbie speaking queue. It publishes a separate `webbie-narrating` marker for source speech-loop echo suppression. While narration is active, the source listener suppresses microphone transcription, so **spoken stop/barge-in during narration remains unfinished**. Stop, pause and resume buttons remain available. Test the marker, voice identity, mic/TTS contention and interruption behavior on the PC before installing.
- Online Natasha may require network access; if unavailable the existing Webbie offline fallback remains. Confirm local voice dependencies and audio output on the PC.
- This update is an open, stacked source PR. Back up the library and preserve the working customized Webbie service, media, encryption and boot. Install only as part of the owner's requested combined upgrade with rollback and live acceptance tests.

## User commands staged

- `Webbie, review this chapter` / `Webbie, review the entire book`.
- `Webbie, give me a deep review of this book`.
- `Webbie, read me the whole book` / `Webbie, read me this chapter`.
- `Pause reading`, `resume narration`, `stop reading`, `cancel review`.

Typed Author chat commands route locally now in source; spoken commands require real voice verification and are not yet enabled by the baseline listener.

## Verification

`tests/test_author_full_reviews.py` verifies entire-source chunk coverage, quick and deep scopes, cancellation, no model calls at startup, no library mutations, and Webbie voice-module reuse. It uses disposable library data and does not upload manuscripts or perform actual narration.

Installation acceptance: launch Author through The Web, choose an imported private test book and chapter, run quick/deep reviews, verify reports reference every chapter, test pause/stop/resume during spoken chapter and full book, compare audible voice to resident Webbie, confirm manuscripts and snapshots unchanged, then restart/rollback-test the full integration.
