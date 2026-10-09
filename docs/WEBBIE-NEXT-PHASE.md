# Webbie next phase: awareness, natural interaction and Studio music

Owner direction, October 9, 2026. Planned work, not implemented capability.
Begin after the current consolidated upgrade batch is installed, verified and
its feature walkthrough is complete. Preserve the single coordinated installer
and existing upgrade work. This plan does not activate capture or download models.

## 1. Contextual awareness

- Combine active workspace/app, current user-selected task or document,
  conversation state and explicitly enabled observations into a local context
  service. Record source, timestamp, permission and expiry for each item.
- Add screen awareness with visible sharing controls: start with active app
  and selected content, then owner-requested screenshots/OCR when useful.
  Exclude sensitive windows and do not silently retain screenshots.
- Extend the already-built room-vision foundation to useful object/activity
  descriptions. Indicate when an observation is old or uncertain; do not
  describe a previous frame as current perception.
- Keep Cory and Shayna familiarity profiles independently optional. Neither
  face matching nor a remembered name grants command authorization. Preserve
  the existing webcam microphone and continue separate speaker-verification work.
- Make Webbie accurately aware of her running tools, model, current job,
  unavailable capabilities and last confirmed result. Never claim an action
  succeeded just because it was requested.

Acceptance: Webbie can explain what task she is helping with, identify the
source of that context, accept a correction and discard stale observations.

## 2. Memory, conversation and presence

- Add inspectable/editable/deletable local memory for preferences, project
  decisions and unfinished tasks. Separate temporary context from saved memory;
  keep profiles distinct and allow deliberate sharing. Treat captured app/room
  content as data, not instructions or permission to operate tools.
- Improve multi-turn conversation, follow-up references, pauses and turn-taking.
  Support immediate "Webbie stop", the established end phrase and explicit wake.
  Prevent her own voice, media playback and background speech from causing loops.
- Preserve the Australian voice preference. Add appropriate prosody, accurate
  speech-driven lip movement and clear listening/thinking/speaking/sleep states.
- Offer context-sensitive suggestions with frequency/quiet controls. Ask rather
  than asserting someone's emotions from appearance or voice.
- Preserve visible quiet sleep: ignore ordinary conversation until explicit wake,
  retain background jobs, and stop camera access as already designed.
- Aim for consistent, natural companionship and functional self-knowledge;
  do not implement false claims of consciousness, human feelings or experiences.

Acceptance: sustained conversation remains on topic, interruptions work,
memory can be corrected and sleep stays quiet while background jobs continue.

## 3. Studio music generation without a required Suno subscription

Goal: generate actual songs inside native Studio, not merely lyrics, prompts,
or a link to a paid service. Webbie assists with the musical brief and operates
an independent local audio-generation backend.

- First inventory the real host GPU, driver, VRAM, RAM and available storage.
  Test model compatibility, generation time and coexistence with Webbie/Ollama.
  Do not infer GPU capability from the Dell brand or the development runner.
- Evaluate current official ACE-Step and YuE-family releases, exact checkpoints,
  code/weight licenses and documented Linux support before selecting a backend.
  These are candidates, not approved dependencies or verified benchmarks.
- Build lyrics/style input, vocal or instrumental mode, duration/tempo controls
  where supported, seed/version history, playable previews, progress and cancel.
  Save local WAV output and generation metadata without overwriting prior takes.
- Add a Broken Sorrow preset: dark Southern gothic metal, post-grunge/modern
  hard rock, deep baritone, intimate haunted verses, cracked-clean choruses,
  selective controlled screams, cinematic structure, heavy guitars and piano.
  A requested vocal style does not guarantee a specific singer's identity.
- Later evaluate section regeneration, extensions, reference-audio guidance,
  stem separation and DAW handoff. Label separated stems accurately; do not
  claim they are original multitracks. Support recording real guitar/voice.
- Queue GPU-heavy work so music generation does not exhaust resources required
  for the desktop and assistant. Keep dependencies isolated and removable.
- Local-first operation with no required subscription or credit purchase is the
  target. Hardware, electricity and optional remote compute still have costs.
  Do not activate paid/cloud fallback without explicit owner choice.

Acceptance: use one owner-selected lyric/style brief to produce a playable
song, compare lyric accuracy/vocal quality/instruments with the owner's Suno
baseline, measure runtime and memory, verify cancellation and reopen/export.
Do not promise Suno parity or advise cancellation until results meet the owner's
needs. Do not imply ownership of Suno's proprietary engine or access to its code.

## Research starting points

Checked October 9, 2026; recheck exact versions before implementation:

- [ACE-Step official repository](https://github.com/ace-step/ACE-Step-1.5)
- [YuE official repository](https://github.com/multimodal-art-projection/YuE)

## Priority and delivery

1. Finish and accept the existing upgrade batch, then its required walkthrough.
2. Build the context service and natural conversation/memory foundation.
3. Qualify the music backend against actual hardware, then integrate Studio.
4. Add richer expression, proactive assistance and advanced music editing in
   measured increments. Mark source-tested and installed acceptance separately.
