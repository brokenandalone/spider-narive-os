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

## What My Voice must eventually mean

The owner's explicit goal is to **record a voice dataset once, then synthesize future studio-sung parts with a recognizable owner voice that is pitch/timing/prod improved**, even when no fresh lead vocal is recorded. The present sample/ACE-Step reference control is a first data collection and creative reference step, **not** the required learned singing identity.

Next work:

- [x] Consented private capture/import UI and WAV/reference safeguards.
- [x] Band arrangement and gender/guest original-singer prompt controls.
- [x] Own-song audio-conditioned cover and extension controls using documented local ACE-Step protocol.
- [x] Add consent-confirmed offline RVC dataset preparation inside Studio AI. Duration probing uses local ffprobe, requires at least 10 minutes of valid recording, creates protected copies plus a SHA-256 manifest and never begins training. No recordings have been collected on the owner's PC by this GitHub work.
- [ ] Record and review a sufficiently varied, clean **real training dataset** over several sessions; aim for 10–30 minutes to evaluate RVC, longer when available. Include quiet singing, sustained vowels, expressive passages, rough and clean techniques. Never auto-enroll from microphone listening or webcam.
- [ ] Test RVC voice conversion training and inference with own licensed recording only. Confirm GPU/VRAM, CPU fallback, model licensing, output identity and artifact preservation. On PC, use official RVC training steps rather than a guessed command. **RVC timbre conversion is not automatic intonation correction.**
- [ ] Generate a lead with ACE-Step, separate its vocal stem with a confirmed local stem-separator, apply the trained owner's voice timbre to that vocal, pitch/timing-polish only by opt-in controls, and remix with untouched backing. Preserve raw source, model seed, generated vocal, converted vocal and final mix separately. Test for artifacts/metal singing screams.
- [ ] Add selectable, locally trained guest-voice profiles only from each singer's permission and own recordings; original AI archetype voices remain available with no enrollment. Never label a text persona as a trained human voice.
- [ ] Add named vocalist timelines and real multitrack independent guitars using ACE-Step `lego`/DAW handoff where supported, then confirm exports.
- [ ] Establish quality and consistency via side-by-side blind listening on owner PC. Do not claim Suno v6 parity until earned.

## Local engine preparation (voluntary)

Run `bash studio/package/music-engine.sh --check` from repository root for read-only inventory. If **and only if** the owner approves heavy data downloads, run `--install` to prepare isolated ACE-Step dependencies in the home directory; `--start` explicitly launches local service (may download weights). Existing Webbie, Kali Bay, KDE, study content and bootloader are unchanged. This is not part of the combined OS installer yet.

ACE-Step API documentation: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md
ACE-Step installation: https://github.com/ace-step/ACE-Step-1.5
RVC source and training guide: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

## Merge and install gates

- [ ] GitHub source test suite passes on branch head.
- [ ] Compare current PC `/usr/local/lib/spider-os/studio` and `study` with source and preserve local modifications.
- [ ] Collect PC GPU and CPU RAM information **without changing packages**.
- [ ] Qualified rollback backup, preflight, and combined install manifest.
- [ ] One combined, reversible install at owner's request. No routine logout or OS reboot while work is incomplete.
- [ ] Smoke test Studio AI UI, mic selection, local recording and source backup.
- [ ] Produce and listen to **one real** local-generated song with optional AI female singer and two distinct guitar roles.
- [ ] Pilot own singing voice conversion only after separately verified model training, dataset consent and audio quality.
