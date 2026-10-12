# Spider Studio v11: Audio Quality, reviewed DAW handoff and Webbie guidance

Development date: October 11, 2026  
Base: v10 Production Board, stacked on v9 Release Desk, v8 Studio Projects, v7 Band Mixer, October 10 Studio AI.

## New source capabilities

**Audio Quality tab:** Select existing mono or stereo PCM WAV files (8, 16, 24 and 32-bit) and run an asynchronous, read-only preflight. Import selected file paths explicitly from Production Board. Check the first and last **8 seconds** of each WAV for sample peak (dBFS), RMS level (dBFS), nearly full-scale sample counts, digital silence, possible DC bias, audio duration, sample rate, channel count and bit depth. A group audit warns about length and sample-rate differences; it will not label a full AI song reference as isolated instrument parts. On-demand only, no microphone, GPU, model call or writes to the source recordings. Stop is supported.

**Limits and honest labels:** These values are measured from bounded PCM windows, not every second of a full recording. Near-full-scale samples are **possible clipping indicators**, not proof that an audio signal clipped. Sample-peak is not inter-sample true-peak or LUFS. The checker does not assess emotional quality, pitch, instrumental identity, crossfade, mastered loudness targets, final playback or timing alignment by ear. Music clips and final mixes still require a human listening pass.

**Production Board DAW handoff:** The new button `Prepare reviewed stems for DAW` preloads the existing MultitrackDialog using individually owner-reviewed WAV tracks and, optionally, the complete song reference with the honest `reference_mix` role. It never mislabels an AI full-song WAV as a separate guitar or lead vocal. The user reviews the dialog and explicitly starts the copy. WAV sources remain unchanged, and copied source recordings begin at zero in the DAW. Exact mixer gain, pan and timing offsets are not automatically translated into a native Ardour project.

**Production Board QC handoff:** `Inspect recordings in Audio Quality` copies current file path selections into the new Quality tab and switches the visible tab. No audio analysis begins until the owner clicks **Inspect selected WAVs**.

**Webbie context:** `What should I do next in Studio?`, `Studio next step` and `What is next in Studio` run a fixed local `production_board.py --next` read-only command. The output provides a generic recommendation inferred from the latest saved checkpoint, or asks the user to relocate a missing WAV. It does **not** speak the title, private lyrics, notes or file paths. Existing `Studio status` and explicit `Open Spider Studio` remain intact. Webbie still cannot start recording, AI training, render or releases from these commands.

## Safety and installation continuity

- Your installed October 10 Studio AI has **not** been changed by these GitHub commits.
- Quality analysis is local, offline, non-destructive and explicit. The GUI runs it in a cancelable worker to keep the desktop responsive.
- The actual PC version, Webbie agent, songs, recordings, models, school data, service files and customized workspaces **must** be compared and backed up before a future combined install.
- The read-only `studio/package/inspect-studio-install.py` now checks v11 source modules.
- `the-web/package/reconcile-native.py` keeps the conservative legacy Studio preservation fixture up to date.

## Source verification and remaining acceptance

Backend and Qt tests cover 8/16/24/32-bit PCM, true digital silence and near-fullscale samples, short-window limits, source preservation, duplicate/symlink rejection, cancellation, grouped mismatch warnings, UI-only opt-in actions, reviewed-only DAW handoffs, no automatic export/copy/model execution, and private Webbie next-step guidance.

A green GitHub CI means only source-level regression coverage passed. No installed-PC WAV device/GPU/microphone, audible mastering, Linux DAW project import or trained personal voice quality can be claimed without on-device tests.
