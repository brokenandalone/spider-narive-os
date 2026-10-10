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

## Merge and install gates

- [ ] GitHub source tests pass on the exact next release candidate commit (the head can change as new features are committed).
- [ ] Compare current PC `/usr/local/lib/spider-os/studio` and `study` with source and preserve local modifications.
- [ ] Collect PC GPU and CPU RAM information **without changing packages**.
- [ ] Qualified rollback backup, preflight, and combined install manifest.
- [ ] One combined, reversible install at owner's request. No routine logout or OS reboot while work is incomplete.
- [ ] Smoke test Studio AI UI, mic selection, local recording and source backup.
- [ ] Produce and listen to **one real** local-generated song with optional AI female singer and two distinct guitar roles.
- [ ] Pilot own singing voice conversion only after separately verified model training, dataset consent and audio quality.
