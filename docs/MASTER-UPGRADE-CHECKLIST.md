# Spider OS master upgrade checklist

Reordered October 9, 2026, late evening, America/Indiana/Vincennes. This order supersedes earlier ordering. Repository: `brokenandalone/spider-narive-os`.

The owner's next priorities are reliable Webbie, preserving PC repairs, contextual awareness and more natural interaction, then Studio music creation with his own voice. **The owner is actively repairing Webbie on the PC in parallel.** Do not build a competing voice fix or overwrite that work. Bring the resulting working files back into GitHub.

Continue GitHub work between installations. Prepare **one combined install per owner request**, not one per day or many small installs. `[x]` completes only the stated source/test/installation task; these are separate from real PC acceptance. Earlier details remain in [the historical checklist](archive/MASTER-UPGRADE-CHECKLIST-before-20261010.md); its older status statements are historical.

## 1. Webbie reliability: PC repair in progress, then source reconciliation

- [ ] **IN PROGRESS ON PC:** reliable wake/answers, multi-turn follow-up, Webbie stop, microphone recovery and correct launcher. Use the result of this repair as the voice baseline.
- [ ] Import the final working agent, TTS, listener and associated voice-gate changes together; preserve speaker authorization, webcam microphone discovery, voice-storage permissions and USB recovery.
- [ ] Verify only Cory and Shayna can authorize voice commands by default. Face recognition does not authorize speakers; basic operation must not require both face profiles.
- [ ] Test interruption while speaking and while an answer is being generated; canceled replies must not speak afterward. Test echo rejection and recovery after failures.
- [x] Restore source conversation history, SQLite memory, saved research topic lookup and bounded non-thinking Ollama requests from the supplied PC brain diff, while retaining configured model selection and new bay names. Focused mocked tests pass.
- [ ] Compare the restored brain with the final current PC files and actual database permissions before installation. No memory database or private conversation is committed.
- [ ] Preserve PC Firefox launch/focus handling, verified Media Center launch, live Forage answers, persistent research queue and accepted-speech popups during agent reconciliation.
- [ ] Verify one voice service, one floating face, login greeting, state indicators and Australian voice.
- [ ] Preserve visible quiet sleep until deliberate wake, with existing background jobs continuing. Retain the owner's end/wake phrases; do not restore obsolete timed wake behavior.
- [x] PR #29 contains camera capture and Qwen3-VL preference changes. Owner subsequently confirms webcam vision works through Webbie.
- [ ] Compare final PC camera files/settings with PR #29 before asserting exact equality; retain optional independent Cory/Shayna face profiles.

## 2. Preserve all PC repairs in one qualified GitHub update

- [x] Compare supplied PC code/diffs with PR #29 head `d41e4b7`; record gaps in [PC reconciliation](PC-RECONCILIATION-2026-10-10.md).
- [ ] Collect final files/hashes after the active PC repair and resolve differences without wholesale replacement.
- [ ] Keep installer blocking for unknown local changes, one backup manifest and tested rollback. Do not whitelist custom files to bypass review.
- [ ] Consolidate compatible PR work; verify CI on exact source revisions, then merge qualified changes. Preserve the frozen release until the replacement is ready.
- [ ] Add qualified Forage changes to the combined install after comparing the installed engine; it is not currently in the combined manifest.
- [ ] On the owner's install request, deliver one frozen revision, preflight, backup, combined installation, activation and acceptance pass. No repeated logouts for source work.
- [ ] Give the complete sequential setup/control tutorial after installation and acceptance.

## 3. Webbie context, memory and natural interaction

Added from the owner's report `2026-10-09_23-04-16_Ways_to_make_Resident_AI_more_human_like_and_life_.md`. Its generic numbered references and empty Sources section do not establish its claims. These are requested development/research directions, not verified capabilities.

- [ ] **Context:** retain the active task, bay, open document and conversation; handle task changes and corrections.
- [ ] **Memory:** record origin/time, separate user facts from guesses, resolve contradictions, allow inspect/correct/delete and test recall across sessions.
- [ ] **Complex recall:** evaluate multi-step project continuity and retrieval within hardware/context limits; measure wrong and missing memories.
- [ ] **Room and screen awareness:** connect consented observations to the active task with visible state, controls and bounded retention.
- [ ] **Natural dialogue:** improve turn-taking, follow-up questions, interruptions, sarcasm and ambiguous phrasing using representative evaluation examples.
- [ ] **Emotion-aware responses:** evaluate tentative interpretation of wording/tone and empathetic language; ask instead of asserting feelings. Do not claim Webbie feels emotions or infer emotion from identity recognition.
- [ ] **Adaptation:** keep reviewable preferences and corrections. Distinguish prompt/retrieval improvements from actual fine-tuning; conversation alone does not establish continuous training.
- [ ] **Advanced training research:** compare models, retrieval, human feedback and optional hybrid approaches against hardware, licenses, privacy and measured usefulness. Neuroscience-inspired methods are research options, not required dependencies.
- [ ] **Interaction effects:** keep clear AI identity and controllable personalization/proactivity; evaluate usefulness and unwanted intrusive behavior over time.
- [ ] Qualify offline operation, selected model fallback and latency before marking complete.

## 4. Studio music generation and production

- [ ] Inventory GPU/VRAM/RAM/storage and select an attainable local music-generation baseline.
- [ ] Review model licenses, song length, lyrics adherence, instrumental/vocal quality and actual generation time.
- [ ] Implement real generation with lyrics/style controls, progress/cancel, saved audio and playback. A controls schema is not music generation.
- [ ] Add the owner's consenting singing reference and evaluate voice fidelity through listening tests.
- [ ] Support Broken Sorrow style, arrangements, iterative edits and DAW/session export.
- [ ] Qualify PR #27 controls against an actual backend; do not claim Suno parity from the specification alone.
- [ ] Verify production launchers, recording devices, PipeWire/JACK routing and project templates while preserving customized Studio tabs/projects.

## 5. Essential desktop controls

- [ ] Qualify Close/Minimize/Restore, taskbar/overview, Firefox focus and unsaved-work prompts.
- [ ] Verify volume/mic controls, input/output switching, mixer and media keys.
- [ ] Verify notifications/history/Do Not Disturb, tray menus and dark/light mode across Qt/KDE/GTK/dialogs.
- [ ] Finish network/Bluetooth/power/brightness/display/drive controls and multi-monitor behavior.
- [ ] Preserve installed wallpapers/purple identity; verify floating-face placement, click-through and fullscreen handling.

## 6. Author and Webbie in every bay

- [x] Owner confirms Author import works and entries open. Do not list the import itself as missing.
- [ ] Verify counts, originals, independent backups, autosave, snapshots and restore.
- [ ] Complete and verify Author website feature parity: library, chapters, canon/characters/timeline, search, comparisons, read-aloud controls and exports.
- [ ] Use Writer in Author, Justin in Studio, Student in Study, Spider in Kali Bay and Cory normally, preserving overrides.
- [ ] Connect Webbie to real scoped actions in every bay, with approval before manuscript edits or risky system actions.

## 7. Forage and Deep Forage evidence quality

**The source-free report defect is an immediate reliability fix being handled alongside priorities 1–2**, before more research is used as an implementation basis.

- [x] Source-tested: skip synthesis when no usable evidence is retrieved and save an explicit incomplete result.
- [x] Source-tested: withhold drafts with missing/out-of-range numeric citations or generic Source Material placeholders; preserve actual links.
- [x] Source-tested: label extracted page evidence versus snippet fallback. Citation-number validation does not verify claim support.
- [ ] Verify real search/provider behavior on the PC; retain the old report as unverified rather than relabeling it.
- [ ] Add claim-to-source support checks, dates/quality and explicit uncertainty. Claims about installed Webbie also need actual code/runtime evidence.
- [ ] Finish research queues, cancel/progress, history, local indexing and source-preserving exports to Study/Author.

## 8. Study and recovery assistance

- [ ] Verify current SNHU coursework, assignments/due dates, dashboard and APA exports.
- [ ] Preserve Word formatting preferences and connect reviewable Webbie assistance.
- [ ] Add sourced, location/date-aware NA/AA lookup and requested reminders.

## 9. Media Center, radio and AI DJ

- [ ] Verify music/movie playback, seek/subtitles/audio tracks, visualizer and actual radio start/stop.
- [ ] Complete DJ transitions, ducking, crossfade, MPRIS and media-key control.
- [ ] Add integrated decoding, legal live TV/IPTV, photos, network libraries, casting and portable DJ workflows.
- [ ] Verify the authoritative Media Center donor/build before salvage; resolve conflicting earlier version references explicitly.

## 10. Recovery, security and remaining bays

- [ ] Maintain backups/read-only health checks throughout every phase; immediately promote an actual disk/boot/data-loss fault.
- [ ] Verify Guardian/Vault and restore a harmless sample. OneDrive remains optional, explicitly connected and limited to approved content.
- [ ] Verify Kali container/package health and Offensive/Purple tools without blindly reinstalling everything.
- [ ] Finish Art Lab, Communications, Dev Bay and other useful bay workflows as dependencies are ready.
- [ ] Plan authenticated remote access and the requested three instances after local reliability.

## 11. Distribution release and startup cosmetics

- [ ] Preserve working encrypted boot and Plasma fallback; qualify remaining startup branding with rollback/boot tests.
- [ ] Reconcile installed Ubuntu and ISO inputs; test BIOS/UEFI/encryption/install/recovery in VMs.
- [ ] Finish reproducibility, receipts and toolchain/security maintenance; do not substitute the old Fedora/Aurora repository for the working native Ubuntu system.

## Current release boundary

This batch changes GitHub source only. The PC repair remains active separately. No install, voice-service restart, model download, private memory upload or boot change is performed here. Final voice reconciliation depends on the working outcome of that PC repair.
