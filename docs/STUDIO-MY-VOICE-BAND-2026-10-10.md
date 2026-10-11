# Studio AI: local band generation and My Voice

**Status: GitHub source implementation; never installed or accepted on the owner PC.**
Branch stacks on the Studio v6/Study workspace PR. Source CI is a unit and simulated API gate, not proof of music-render quality.

## What works in source

1. Local ACE-Step 1.5 client: native song description and lyrics, WAV takes, preserved jobs, local-only API.
2. Three editable original vocal roles: deep original baritone, feminine alto/soprano, tenor, and original Jason/J-Cold character roles. Vocal line assignments are descriptive; current engine may ignore them.
3. Separate roles for guitarist 1 and guitarist 2, rhythm/lead, plus bass, drums, and piano. These are **prompt roles in a mixed WAV**, not verified independent audio stems.
4. Vocal workflows: text-to-song with generated AI singers; audio-conditioned cover from an existing owner performance; accompaniment continuation using ACE-Step `complete`. All audio sent to **local-only ACE-Step**.
5. Record a 30-second, user-started mono WAV using existing `arecord`, or import an owned 64MiB-or-smaller WAV, MP3 or FLAC sample. Voice files stay under `~/Documents/Spider Studio/Music/My Voice` (0700 directory, 0600 files). Recording does not alter or restart Webbie. Microphone sharing/ALSA access requires real PC qualification.
6. Optional personal voice-reference audio uploaded to the **local** generation engine as ACE-Step style conditioning. It does **not** automatically clone the user's recognizable singing voice. Original source takes and reference audio are copied privately into a song job folder before submitting. No cloud model or remote URL is accepted by the music adapter.
7. RVC `infer/cli.py` support for converting an **isolated WAV vocal** using a **separately trained** trusted local RVC model. Vocal conversion is not itself model training or pitch/timing correction.
8. A private FFmpeg WAV mixer with separate converted-voice and backing inputs, two volume controls, an audio limiter, cancellation and an immutable-original policy. It saves new 48 kHz WAV exports with private job receipts. Studio's source UI offers this final-mix stage, and automatically fills the converted-voice path after RVC succeeds.
9. An opt-in training-engine script `studio/package/voice-engine.sh`. Its read-only `--check` reports readiness, `--clone` obtains upstream RVC only when requested, `--prepare-cpu` installs CPU dependencies to an isolated venv only when requested, and `--launch-local` uses a **source-checked, private** WebUI copy. Unlike upstream's default Gradio bind, both the visible training UI and the port probe are patched to loopback, with public sharing disabled. Unknown changes fail closed. **This is a manual RVC training tool, not yet an automated one-click train-and-sing pipeline.**
10. PyMSS generated-song separation via `studio/stem_separation.py` and a new Studio AI control. It invokes the documented RVC PyMSS vocal separation model using local Python and protected per-job output; on first explicit use the model may download weights. The tool opens the output folder and asks the owner to audition and identify the resulting WAV files rather than assigning potentially mislabeled stems automatically. The current split step does **not** prove quality, eliminate backing bleed, or automatically convert the extracted singer into the owner profile. Real separation is still dependent on a trained-model install and PC acceptance.

## Training workflow newly implemented in the Studio source

1. **Check My Voice training readiness** measures real media duration with local ffprobe, reports usable/rejected clips, and shows how much remains of the ten-minute minimum. It runs outside the UI thread and does **not** train a model.
2. **Prepare private RVC training dataset** asks for voice-owner consent, copies samples into an owner-private directory, saves SHA-256 checksums and never alters source recordings.
3. **Open prepared training set / Copy RVC training audio folder** gives the user the exact path for the separately installed local RVC training UI. Both controls remain disabled until a prepared dataset is verified.
4. **Check training setup** calls the opt-in helper in read-only mode from a background worker; it inventories local RVC/Python/GPU/disk prerequisites.
5. **Open local RVC training interface** requires a new explicit confirmation, runs the guarded loopback-only training UI as an ordinary user-managed process and has a Stop control. Opening the interface is not itself model training; the owner must configure and start their own training inside it.
6. Once real trained owner voice-model and index files exist, Studio can perform conversion of selected isolated vocal WAVs and optionally chain conversion into its private final WAV mixer. The generated-song stem separator requires real local PyMSS dependencies and listening checks before using its results.

All the above have GitHub source tests. **No user recordings, trained voice weights, on-device RVC setup, or end-to-end listening acceptance have been produced by source commits.**

## Generated song → trained voice → finished mix (source workflow)

1. Generate an original song with Studio AI and choose its saved WAV take. **Send take to vocal separator** fills the separation source field but does not start a model or download anything.
2. **Separate vocals and backing** requires explicit confirmation first, because PyMSS may download large model weights. The extraction can be stopped without modifying the generated take.
3. A native review list displays the extracted WAV candidates. The user auditions each and manually chooses **Use as singing vocal** or **Use as instrumental**. The app does not trust filenames or silently assume an extracted track is clean.
4. A vocal selection populates the local RVC conversion source; an instrumental selection populates the final mix backing. The same WAV cannot serve both roles. Converted vocal selection is cleared when a new singing source is chosen.
5. **Convert My Voice and make final mix** uses a separately, genuinely trained and trusted owner RVC model, then produces a new WAV while keeping the original recording, separated tracks and converted vocals.

Each separation job now saves a private `separation.json` receipt listing the original WAV, the selected separator model, all valid extracted WAV candidates, and each candidate's deliberately **unassigned** role. Stereo/mix outputs and intermediate files stay local. The RVC conversion and PyMSS adapters also accept the standard Linux virtual-environment Python executable symlink; audio sources and pretrained voice-model symlinks remain rejected. Both changes are covered by source tests.

**Source implementation is not acceptance:** a real GPU/CPU qualification, model installation, consented owner-voice training, separation-quality audition and full production render have not occurred on the user's PC. In particular, extracted voices may contain artifacts, the original AI singer can bleed into the backing, the generated two guitars may be inseparable, and the output does not yet imply pitch correction or a verified Suno v6 substitute.

## What My Voice must eventually mean

The owner's explicit goal is to **record a voice dataset once, then synthesize future studio-sung parts with a recognizable owner voice that is pitch/timing/prod improved**, even when no fresh lead vocal is recorded. The present sample/ACE-Step reference control is a first data collection and creative reference step, **not** the required learned singing identity.

Next work:

- [x] Consented private capture/import UI and WAV/reference safeguards.
- [x] Band arrangement and gender/guest original-singer prompt controls.
- [x] Own-song audio-conditioned cover and extension controls using documented local ACE-Step protocol.
- [x] Add a native check of usable singing duration/rejected clips plus the private dataset folder open/copy handoff.
- [x] Add guarded user-confirmed local RVC trainer UI launch/stop and nonblocking read-only dependency check (source and mock tests only).
- [x] Add consent-confirmed offline RVC dataset preparation inside Studio AI. Duration probing uses local ffprobe, requires at least 10 minutes of valid recording, creates protected copies plus a SHA-256 manifest and never begins training. No recordings have been collected on the owner's PC by this GitHub work.
- [ ] Record and review a sufficiently varied, clean **real training dataset** over several sessions; aim for 10–30 minutes to evaluate RVC, longer when available. Include quiet singing, sustained vowels, expressive passages, rough and clean techniques. Never auto-enroll from microphone listening or webcam.
- [ ] Test RVC voice conversion training and inference with own licensed recording only. Confirm GPU/VRAM, CPU fallback, model licensing, output identity and artifact preservation. On PC, use official RVC training steps rather than a guessed command. **RVC timbre conversion is not automatic intonation correction.**
- [x] Connect separately converted RVC isolated-vocal WAV and a provided instrumental WAV in a private, reversible final-mix workflow. This does **not** automatically separate stems from a generated song.
- [x] Create a read-only training-engine audit and explicit user-home RVC CPU setup and loopback WebUI launcher. On-device RVC, model weights and training have **not** been installed or qualified.
- [ ] Generate a lead with ACE-Step, separate its vocal stem with a confirmed local stem-separator, apply the trained owner's voice timbre to that vocal, pitch/timing-polish only by opt-in controls, and feed the resulting stems into the existing final mixer. Preserve raw source, model seed, generated vocal, converted vocal and final mix separately. Test for artifacts and aggressive metal vocals.
- [ ] Add selectable, locally trained guest-voice profiles only from each singer's permission and own recordings; original AI archetype voices remain available with no enrollment. Never label a text persona as a trained human voice.
- [ ] Add named vocalist timelines and real multitrack independent guitars using ACE-Step `lego`/DAW handoff where supported, then confirm exports.
- [ ] Establish quality and consistency via side-by-side blind listening on owner PC. Do not claim Suno v6 parity until earned.

## Local engine preparation (voluntary)

Run `bash studio/package/music-engine.sh --check` from repository root for read-only inventory. If **and only if** the owner approves heavy data downloads, run `--install` to prepare isolated ACE-Step dependencies in the home directory; `--start` explicitly launches local service (may download weights). Existing Webbie, Kali Bay, KDE, study content and bootloader are unchanged. This is not part of the combined OS installer yet.

For RVC, run `bash studio/package/voice-engine.sh --check` first. Only after the hardware and official model requirements are verified, the owner can explicitly use `--clone`, `--prepare-cpu` or a manual CUDA setup, then `--launch-local`. The trainer is intended for use at `http://127.0.0.1:7865`; upstream may choose another local port when occupied. No background trainer is started by default. **Never load unknown RVC .pth files**: model deserialization may execute code. The official RVC training UI is used to create training configuration, train a model and save the model/index from the owner-authorized dataset. No model-quality guarantees can be made before real listening tests.

ACE-Step API documentation: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md
ACE-Step installation: https://github.com/ace-step/ACE-Step-1.5
RVC source and training guide: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

## Private, reusable voice-model selection and listening checks

Studio can now **remember one owner-confirmed local RVC model** under the private My Voice directory without copying model weights or loading a PyTorch model merely to store a preference. Optional local `.index` selection is also retained. The owner must explicitly confirm the files are authorized before registration. Stored paths include file size and modification metadata; if either file is missing or has changed since selection, Studio refuses to restore the stale pointer and asks the owner to reselect it. The **Forget saved model selection** control deletes only the private pointer, never model weights, audio recordings, or training datasets.

The restore control only populates fields. **It cannot prove the selected model was trained correctly or sounds like Justin Therapy.** Model files must be trusted and locally created; unsafe third-party `.pth` files can execute code when loaded by a backend. Once a converted vocal and a finished song exist, separate listening controls let the owner audition them with the installed audio player, with each WAV revalidated before launch.

## Merge and install gates

- [ ] GitHub source tests pass on the exact next release candidate commit (the head can change as new features are committed).
- [ ] Compare current PC `/usr/local/lib/spider-os/studio` and `study` with source and preserve local modifications.
- [ ] Collect PC GPU and CPU RAM information **without changing packages**.
- [ ] Qualified rollback backup, preflight, and combined install manifest.
- [ ] One combined, reversible install at owner's request. No routine logout or OS reboot while work is incomplete.
- [ ] Smoke test Studio AI UI, mic selection, local recording and source backup.
- [ ] Produce and listen to **one real** local-generated song with optional AI female singer and two distinct guitar roles.
- [ ] Pilot own singing voice conversion only after separately verified model training, dataset consent and audio quality.


## Independent band stem mixing (October 11 source upgrade)

Spider Studio AI now has an **independent eight-track offline band mixer** using locally available FFmpeg. Supported audio roles: instrumental bed, trained My Voice / lead vocal, guest or female vocalist, rhythm guitar, independent lead guitar, bass, drums and keyboards. Each selected role takes its **own real WAV** file and gain from 0.00 to 2.00; at least two different sources are required. The source files remain untouched.

The existing verified vocal conversion handoff populates the lead-singer slot; verified manually selected instrumental separation populates the bed slot. Other isolated stems are chosen by the owner from local WAVs (e.g. recorded in a DAW). AI text instructions about a second guitarist or guest vocalist **do not** themselves create separate stems, and PyMSS must not be represented as reliably separating all eight instruments.

The mixer runs in a background thread, offers an explicit stop control, generates a private stereo 48 kHz 24-bit WAV with limiter and a permission-restricted provenance receipt/log under **Documents/Spider Studio/Music/Band Mixes**, and lets the owner audition the output. It does not overwrite, train, upload, or delete models/audio. Inputs are checked for WAV headers, distinct files (including hard links), unsupported roles, symlinks and invalid gain. No shell commands or forced overwrites are used.

**Evidence:** four local backend regression tests passed in isolated testing and FFmpeg successfully rendered a short real two-track PCM sample. New Qt behavior is regression-covered in source, but GitHub CI and the user's real Spider OS Studio launch/mixer/audio-device acceptance must still be checked. The GitHub development branch is **not** proof of installation; preserve the single backup-first combined install gate.


## October 11 source upgrade: true multitrack DAW sessions

Studio AI now includes **Build multitrack DAW session**. The new modal lets the owner choose independently recorded or explicitly separated PCM WAV files and label lead vocal, additional backing singers, rhythm guitar, lead guitar, bass, drums, keys, other instruments, instrumental bed and full-song reference mix. The tool supports up to 24 distinct WAVs, an optional explicit BPM, and a user-supplied project title. A source WAV cannot be reused as two supposedly independent parts.

The original audio is NEVER modified. On explicit export, Spider Studio copies the actual recordings into a fresh private session folder under **Documents/Spider Studio/Music/Multitrack Sessions**, retains the input sampling properties, computes per-track SHA-256 values, and writes \`session.json\`, \`tracks.csv\`, and a human-readable import guide. The GUI runs large copies in a cancellable worker so the window stays responsive. File and directory permissions default to owner-only; existing output sessions are never overwritten. No model download or training is involved in this function.

**Important limitation:** A generated ACE-Step song is a composite reference WAV. Merely naming one copy "lead guitar" or "female backing vocal" would NOT create an independent track, so the new exporter refuses duplicate input files. It does not automatically infer audio stem roles, isolate two guitar players, infer musical tempo, align late recordings, or claim a fully separated AI arrangement. Actual guitar/vocal stems must be separately recorded or reliably extracted and listened to first; all exported tracks are placed at zero for manual alignment in a DAW (Ardour/Qtractor/Audacity or equivalent).

Regression coverage checks genuine two-guitar plus guest vocal session structure, input integrity, no-overwrite copies, private file permissions, missing or invalid audio, symlink rejection, deliberate stop, duplicate source refusal, CSV formula safety and a native editor handoff. This is **GitHub source only** until exact-head CI and PC tests pass; no local Studio files or previously recorded songs have been changed.

Remaining next steps: qualify a locally trained My Voice identity model, create a real distinct AI vocal stem and two actual isolated guitar performances, confirm latency and sample-rate import on the user's Linux DAW, and audition the full arrangement before claiming Suno-like track independence.


## October 11 major production session: reusable mix console

New stacked Studio source branch introduces an end-to-end **existing-WAV production session** workflow:

1. Export a private multi-WAV project with source hashes using the October 11 multitrack exporter.
2. Open **Reopen, audition and mix saved session** from Studio AI, or use **Reopen saved session and mix** from the multitrack dialog.
3. Studio checks every expected numbered WAV, PCM properties and the recorded SHA-256 values before accepting the project. The original source paths in the JSON are informational and are not accessed.
4. Adjust up to 24 saved WAV parts with individual gain (0–2), stereo pan (-1 to +1), mute, solo and positive start delay (0–20 seconds). Full-song reference mixes are excluded by default, and must be explicitly enabled to avoid doubling the same instruments.
5. Save multiple private named **mix presets** in the verified session. Restore them only while the original track fingerprint still matches, with no audio rendering on restore.
6. Render a new 48 kHz, 24-bit stereo WAV using local FFmpeg, preserving every original project and input recording. Fresh render receipts include the exact input hashes and chosen controls. Both verification and rendering use nonblocking, stoppable background workers.
7. Use **Check sampled audio quality** for a quick, explicitly **noncomprehensive** scan of up to the first and last five seconds of each track. It shows peak/RMS and flags sampled silent/clipped regions, DC offset, and sample-rate mismatches. It is not a full-track mastering, phase or vocal fidelity analysis.

Source regressions cover tampered WAVs, path confinement, safe non-overwriting export, independent guitar/vocal controls, pan/delay filtering, actual FFmpeg render, native Qt mixing, persistent presets, and sampled audio-quality checks. **Source CI is not proof that full-song AI stems have been created or that a singer model is trained.** It does not modify the owner's PC or Webbie until a separate backup-first release gate passes.

Pending: the user's live PC hardware and audio-engine check; training and listening to a genuine authorized Justin Therapy vocal model; isolated per-instrument AI generation or verified separation; GUI accessibility scaling for small screens; validating real recordings and audition quality in Ardour or Qtractor; reconciling stacked Studio PRs and customized installed files before any installation.


## October 11 major Studio production upgrade: Mastering Desk and recording guides

This **development-source-only** stack adds an opt-in Mastering Desk after the real 24-track mixing stage and next to Studio AI. A selected completed WAV can be processed through a **measured two-pass EBU R128 FFmpeg \`loudnorm\` workflow**. The three preset targets are *balanced streaming reference* (-14 LUFS, -1 dBTP), *dynamic album reference* (-16 LUFS, -2 dBTP), and *modern rock reference* (-11 LUFS, -1 dBTP). These are user-selectable **targets, not promises of platform compliance, quality, or actual peak values**. Result receipts include both measured source and measured output loudness, source SHA-256, target values and output files, under owner-private folders. A fresh 24-bit/48-kHz stereo WAV is the primary export; FLAC and MP3 listening/distribution copies are optional and require compatible local encoders. Each source WAV remains unchanged, and cancel/timeout cleanup is protected. Mastering is **never** started automatically by importing a song, creating a mix or opening the dialog.

CI was extended to install FFmpeg in the **temporary GitHub runner only**, allowing real output WAV and Qt regression tests to execute rather than relying exclusively on mock calls. Real device quality checks, platform metadata, artistic mixing/mastering and owner listening remain required.

For recording the actual two guitarists, guest singers, bass and drums independently, Studio now offers a **Create recording click guide** control inside the DAW-session builder. Set a quarter-note tempo (40–240 BPM), 4/4, 3/4 or 6/8 meter, count-in (0–4 bars) and the bar count. The tool writes a new private 48-kHz stereo PCM click WAV plus count-in and bar timestamps. Click guides are classified \`click_guide\` within exported Studio sessions. **The session mixer always excludes that role, even if the user explicitly includes a composite reference mix**; it is a tracking aid, not musical drums or a generative song stem. Duration is capped at ten minutes, files are new/non-overwriting, and export supports cancellation. The guide is not automatic drum programming, microphone capture or a fully aligned DAW project.

Source regression coverage includes real PCM guide samples and exact duration, musical bar markers, invalid BPM/meter rejection, stop behavior, session role routing, accidental-guide-in-master prevention, mastering target validation, silent/corrupt audio rejection, original-hash preservation, native GUI handoffs and measured FFmpeg renders.

**Release gate remains unchanged**: no automatic merge, local engine install, My Voice training, or changes to Webbie/boot/service configuration. Reconcile installed PC Studio/Webbie customizations, perform one combined backup-first installation on the owner's chosen daily batch, verify the actual machine's audio stack and restore path, then audition music and test each GUI flow.


## October 11 next major Studio AI session: quality-gated My Voice and recoverable song jobs

The latest **GitHub development branch** extends the owner-only My Voice pipeline without pretending a singing model has been trained. **Audit My Voice sample quality** previews the first 12 seconds of each WAV/FLAC/MP3 locally with FFmpeg/ffprobe. It reports sample RMS/peaks, near-clipping flags, DC offset, silent/very quiet samples, durations and SHA-256 duplicate content. It caps inspection at 256 source recordings and 2 GiB of recorded files. This sampled gate cannot establish full-clip acoustic suitability, singer identity, mic permission, safe model weights or trained-model quality. Users must listen to their recordings and choose which data are authorized.

After explicitly consenting to prepare a training dataset, **Prepare separate train and holdout audio** verifies every staged clip's original SHA-256 and actual audio duration, rejects missing/symlinked/deduplicated or manipulated files, then makes fresh physically separated \`train/audio\` and \`holdout/audio\` private folders. The held-out evaluation copies are NOT mixed into the train-only directory; split receipts name every clip, report remaining time to reach ten full minutes **in the training partition after holdout**, and explicitly mark \`training_started: false\`. The UI's Copy RVC audio button now prefers the split's \`train/audio\` after such a split exists, while the legacy full-dataset selection remains explicitly labeled **no holdout** for compatibility with prior installed usage. No weights, indexes or model trainer are created automatically.

A separate Studio AI **Unfinished local song jobs** list now discovers already submitted ACE-Step jobs with saved task IDs. **Resume selected existing render** reconnects only to the original loopback endpoint and queries \`/query_result\`; it **never** calls the generation submission route \`/release_task\`. The code refuses unexpected existing WAVs, concurrent job writers, invalid manifests or unknown IDs, preserves already downloaded original takes, and allows stopping the wait without restarting the service or discarding the original task. This improves continuity on slow or interrupted GPU renders; it does not guarantee the backend retained an expired task.

These source features are additions to stacked draft PR #59, not machine installation or proof that RVC/ACE-Step, GPU, real voices, actual multi-singer tracks, online music models or Webbie actions work on the owner's Dell. Continue the agreed **one owner-initiated systemwide installation per day**, with a combined backups/preflight/rollback check and device acceptance.


### Webbie-ready read-only Studio query bridge

\`studio/webbie_adapter.py\` now exposes a small explicit query allowlist for a future resident Webbie integration: \`capabilities\`, \`status\`, and \`pending_jobs\`. The first reports what the source interface can plan; the second checks only local FFmpeg/ffprobe executables without waking any engine; the third counts unfinished jobs but **redacts song names, task IDs and private paths**. A command-line entry point can be run explicitly with \`python3 -m studio.webbie_adapter status\` once that package is installed.

**This is deliberately NOT connected to the live Webbie resident process yet**. It cannot activate microphones, control the desktop, train voice models, render songs, contact ACE-Step, access external networks, or bypass the owner's established Cory/Shayna voice-user rules. Future Webbie integrations must enforce speaker permissions in the resident agent and obtain explicit confirmation for consequential operations. This code is source-only and should not be portrayed as active Jarvis-level control.
