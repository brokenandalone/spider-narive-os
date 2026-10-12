# Spider Studio v10: Production Board and Webbie status bridge

Date: October 11, 2026  
Builds on Studio v9 source, which builds on v8 and the already installed October 10 Studio AI development work.

## Major additions

**Production Board tab:** A new scrollable tab next to Studio AI, Band Mixer and Release Desk. Track each song through a user-reviewed reference WAV, true isolated/recorded WAV stems, finished mix, and release preparation. Assign a song title and private production notes.

**Versioned production library:** All checkpoints save into unique `~/Documents/Spider Studio/Music/Production Sessions/session-*/revision-*.json` entries. Revision saves are explicit and append-only; old versions are never overwritten. They store paths and choices, not recorded audio, model weights or passwords. Missing WAV files are reported at load without deleting files. No background indexing or cloud network access.

**Safe actual cross-tab handoff:**
- *Use selected Studio AI song take* sets the full-song reference field. It never claims the generated WAV contains independent guitar/vocal tracks.
- *Send reference to AI separator* puts the path into the existing `separation_source` field and opens Studio AI. The user still explicitly approves local model access and executes separation.
- *Send reviewed stems to Band Mixer* requires at least two distinct, validated WAVs and an additional confirmation dialog before replacing only the mixer source path fields. Current gain, pan, mute, solo, offsets and files are unaffected. It never starts a render.
- *Use last Band Mixer WAV* selects a completed rendered file as the final mix checkpoint.
- *Send finished WAV to Release Desk* selects the final WAV for manual format export. It never renders, uploads or publishes.
- Editing a reviewed source path resets its approval check until the user reauditions and confirms the file. Imported source references are not autoapproved.

**Webbie read-only integration:** Webbie can answer the explicit voice/text commands `Studio progress` or `Studio status` using a fixed read-only local helper and speak a minimal stage/count summary. It does **not** read song title, lyrics, production notes, voice recordings or full file paths in that summary. `Open Spider Studio` launches the actual installed Studio application script and reports failures rather than pretending it opened. The bridge does not authorize Webbie to manipulate recordings, train models, record a microphone, change mixer settings or publish content.

## How to use

1. Create a song in Studio AI or record an original idea.
2. Go to Production Board, load the selected AI take as a reference, and save a named checkpoint.
3. Review and/or isolate source stems with the existing Studio AI separator or independent recordings. Listen to each WAV before selecting its **I reviewed** box.
4. Explicitly send at least two confirmed stems into Band Mixer. Render and listen there. Bring the final WAV back onto Production Board.
5. Send the finished WAV into Release Desk; review formats and export only when chosen.
6. Save new checkpoints at important milestones and retrieve previous versions from the session list.

## Critical distinctions and limitations

The Production Board is a songwriting-to-export *workflow coordinator*, not a new music generation, stem independence classifier, trained RVC model, DAW automation engine or mastering product. User verification means the owner confirmed listening; it is not forensic proof the stem is isolated. The real Studio AI engine and RVC capabilities still depend on separate local installs/model qualification. This branch does not upgrade model quality or enable generalized Jarvis-like autonomous desktop control.

The basic Webbie integration is constrained to **read-only session status and explicit Studio launch**. It does not yet offer full spoken "mix these tracks" controls. No change here asserts that today's features have been installed on the owner's PC.

## Safety and next release gates

The owner confirmed that the October 10 Studio AI is already installed. **Do not replace it with source from another branch without comparing hashes, inspecting owner-customized files and making a reversible backup.** `studio/package/inspect-studio-install.py` lists differences in Studio v10 and the Webbie agent without modifying either.

Source and offscreen Qt tests cover append-only revisions, symlink and corrupt-file rejection, preservation of source bytes, missing-file warnings, no private text in Webbie summary, explicit source approvals, non-generating tab handoffs, and fixed Webbie command routing. GitHub CI success is source verification only. Actual PC audio, installed service microphone behavior and production quality are still acceptance gates.
