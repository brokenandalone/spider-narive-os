# Spider Studio AI: own-voice song generation (owner priority, 2026-10-09)

Status: initial local generation source implemented; **not installed functionality**. See [implementation and v6 comparison](STUDIO-AND-SCHOOL-2026-10-10.md) for exact supported behavior and pending acceptance. Developed separately from the currently installed and owner-reconciled release. No downloaded model, training job, camera/microphone activation or paid service is authorized by this document.

## North star

Inside native Spider Studio, Webbie helps the owner compose, audition, revise and export full original songs with convincing vocals, guitars, bass, drums, piano and production. Owner recordings of **their own singing** provide the vocal identity and performance references, especially baritone, cracked-clean/raspy delivery and selective controlled screams. Suno is the listening baseline, not a licensed backend, copied implementation or guaranteed quality bar. The goal is no required monthly generative-music subscription, subject to real hardware and optional compute costs.

## Three vocal modes, in order

1. **Preserve my actual take (highest identity fidelity).** Record/import isolated owner singing, retain that waveform as the main vocal, and generate/rearrange accompaniment around it where the selected backend can do so. Never relabel AI-converted audio as a live recording.
2. **Convert a generated guide vocal into my voice.** Generate song/guide vocal; separate vocal and accompaniment; apply opt-in singing-voice conversion from an owner-owned singer profile; remix and audition. Evaluate zero-shot Seed-VC (short permitted reference) and trained RVC (cleaner, longer curated dataset) in isolated environments. Compare pitch stability, sibilants, grit, high notes and scream artifacts; never assume perfect identity preservation.
3. **Generate directly with voice conditioning** only if the specific music backend/weights and independent listening tests demonstrate reliable speaker identity. Reference-audio timbre/style influence is NOT proof of voice cloning. Experiment with licensed fine-tuning/LoRAs separately, without promising that a music LoRA learns a person's voice faithfully.

These must remain selectable; no source vocal is deleted or overwritten.

## Candidate generation backends

- **ACE-Step 1.5:** first hardware-dependent candidate for lyrics-to-song, instrumental generation, reference-based covers, repaint/infill and local API. Official repo https://github.com/ace-step/ACE-Step-1.5; MIT-reported project license, but audit checkpoint and third-party dependencies independently. Determine configuration from actual GPU and VRAM, not machine brand.
- **YuE2:** high-quality comparative candidate with score/lyric planning and covers (official https://github.com/multimodal-art-projection/YuE); current documented Linux setup requires Python 3.12, NVIDIA BF16 GPU and **24 GB VRAM**. Authors report competitive benchmark settings but this is not user-validated performance. Its weight license is CC BY-NC 4.0 with additional permissions for musicians/creators; review exact terms for each use.
- **Seed-VC:** dedicated singing voice conversion with a short authorized reference. Official https://github.com/Plachtaa/seed-vc (GPL-3.0 code shown).
- **RVC:** candidate for longer-data singer identity refinement. Official https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI (MIT code shown); models/data/component licenses need review.
- Optional separation: test a locally licensed source separator (e.g. Demucs family) and export converted/split stems as estimates, never as the original multitracks.

The code for voice conversion, music generation and mixing is separate from the resident Webbie voice/TTS and microphone wake listener.

## Native Studio UX

A **Studio AI** tab with:
- Song title, lyrics with section markers, genre/production directions, target duration/tempo/key when supported, instrumental/vocal switches.
- Private Singer Profiles: "Record sample", "Import dry singing", "Review/trim", "Train/prepare", "Audition", "Delete profile". Explicit consent and retained-file inventory. No profile required to use instrumentals.
- A 3-mode selector: **Use my real vocal / Sing in my voice / Standard AI singer**.
- Broken Sorrow preset: dark Southern gothic metal, post-grunge, modern heavy rock, 7-string/heavy guitars, cinematic piano, deep baritone, haunted verses, cracked-clean choruses, restrained controlled screams, organic performances.
- Queue, progress, cancel, resource estimate and reproducible seed/settings. Generate multiple takes, A/B audition, version every output.
- Section regeneration/extend and lyric repair when provider supports those operations. Export full mix + WAV/FLAC audio + converted vocal/estimated instrumental stems + session JSON; later DAW handoff and conventional recording/mixing.
- Webbie can prepare descriptions, operate a permission-gated job queue, report genuine progress/errors, and compare output against owner feedback. She never falsely claims she heard or rendered a song without the corresponding result.


## Suno v6 feature benchmark (confirmed October 9, 2026)

Official release: https://suno.com/blog/introducing-v6 (September 9, 2026). Official FAQ: https://help.suno.com/en/articles/13924481 and https://help.suno.com/en/articles/6141377; own-voice workflow https://help.suno.com/en/articles/11362369.

Suno **v6 / v6-wild / v6-mini** are distinct quality/creativity/speed choices; the classic creative controls are **Weirdness** (Safe -> Chaos; 50 nominal), **Style Influence** (Loose -> Strong), and **Audio Influence** (appears when a suitable audio reference/upload is selected). v6 also documents a **Variety** slider that adjusts/rephrases style prompts (0 means no changes) and **Max Mode**, costing extra credits to devote more computation to longer songs, covers and vocal/style consistency.

The product should provide distinct user-facing sliders (0-100): Weirdness, Style Influence, Audio Influence and Variety, and a Standard/Max-quality switch. Keep their values in saved session/variant metadata. These are *product-level intentions*, not compatible magic numbers in every model: each backend capability adapter must display which controls are implemented, approximate, or unavailable. For ACE-Step, possible separately testable adapters include sampling-temperature/seed for exploration, prompt/caption and guidance for style adherence, audio_cover_strength for source/reference influence, and steps/quality settings; do not hard-code linear slider mappings without testing actual results.

Add **Creative / Experimental / Quick** modes as *Spider Studio modes*, not claims that we run Suno's proprietary v6, v6-wild or v6-mini checkpoints. Use multi-take and side-by-side audition, seed control, explicit user-intended style tags and non-destructive song variants.

**Primary voice behavior clarified:** a user may supply 15 seconds to 4 minutes of singing to Suno's Voices workflow, pick up to 2 minutes, verify voice ownership, then generate new performances with the uploaded reference (official Suno help). Spider Studio must prioritize **generate a NEW sung take in the owner's vocal identity while cleaning timing/intonation/production**, without demanding that the original waveform remain unchanged. Actual-take preservation is an additional, selectable mode, not the default Suno-style workflow. Avoid oversmoothing, unrequested pitch shifts and complete removal of rasp/screams. Offer amount of cleanup and "identity preservation" as separate controls only where technically supported.

The Suno v6 FAQ says custom-trained models migrate to v6. Some older Suno Voice help still tells users to choose v5.5, which is inconsistent with the September v6 retirement announcement; do not assert exact v6 Voice-model compatibility without checking the current Create UI or an updated voice-specific support statement.

v6's benchmark also includes natural-language **edit a selected section**, **replace a lyric**, **multi-source mashups**, **sample/isolate/build around a riff**, **image/video/music reference inputs**; Suno Studio 2.0 adds MIDI, built-in synth/effects, automation, and a chat bar. These are long-term feature comparisons, not implemented source behavior.

### Voice-first sequence and acceptance test

1. Owner records/imports 30-120 seconds of dry expressive singing in their own voice, including clean, gritty and higher register takes. Any voice profile requires owner consent and local storage by default.
2. Save a private singer profile and run a new text-to-song vocal generation plus (as needed) locally licensed singing voice conversion. Keep the original unchanged; optional cleanup controls should target pitch/timing/noise while preserving distinctive character.
3. Expose four creative sliders and save every setting with every take; if backend cannot honor one, say so and disable/explain it.
4. With *the same* lyrics/style, A/B compare generated vocals and full arrangements against owner's existing Suno v6 output, listen for audible identity, syllables, grit, belting/screams and timing.
5. Permit local remix/instrument variants and source-preserving edits; measure actual GPU, quality, time, and costs, and don't imply parity until demonstrated.

## Before any model installation

Read-only installed PC audit: GPU vendor/model, dedicated VRAM, system RAM, disk, GPU driver, Python, FFmpeg, Ollama and existing PipeWire/Studio usage. Qualify 2B/offload/CPU options if no suitable GPU; large CPU jobs may be impractically slow. Reserve VRAM for Webbie/desktop; throttle/queue jobs and allow cancel. Download exact version-pinned models only after informed owner approval; prefer off-machine fallback only when voluntarily chosen, with explicit price and privacy disclosure.

## Owner voice dataset

Prefer clean dry **singing**, not only speech. Capture multiple registers: soft baritone, sustained notes/vibrato, chorus belting, gritty transitions and **safe existing recordings** of controlled screams (do not encourage vocal strain). Use 24-bit WAV when available, no instrumental bleed, no doubling, little reverb/FX and consistent microphone distance. Start with a short owner-approved reference to test zero-shot conversion; curate 10+ minutes (more as results justify) for trainable models. Never publish, upload, sync, or silently reuse these files for another person. Consent and identity of anyone other than the owner are required independently.

## Acceptance gates

- Successful local render (not mocked), no paid-service dependency for the chosen mode, truthful progress and cancel.
- Sampled generated and real-vocal workflows that do not overwrite source songs.
- Blind A/B owner listening versus their own Suno references on production, lyric correctness, intelligibility, voice identity, emotion, grit/screams, mix and runtime; record actual GPU/RAM/time and failed cases.
- At least one 3-minute song with intro/verse/chorus/bridge/outro where supported; play/reopen/export the mix; editing re-renders only supported spans.
- No "Suno parity" or "your voice cloned" label until demonstrated on the owner's recordings. No recommendation to cancel Suno until actual listening results satisfy owner.

## Delivery gates

1. Hardware readiness and licensed prototype candidate selection.
2. Native Studio AI tab + permission-gated job manager + standard AI song and instrumental generation.
3. Owner vocal preservation + short-reference singing conversion; test profile storage/delete and multi-take comparison.
4. Longer singer training or fine-tuning if needed; mix and editable production tools.
5. After a successful owner-PC acceptance pass, integrate the source changes into **one** versioned, reversible requested Spider OS installation. Do not modify the just-installed combined release in place.

Research verified from official repositories October 9, 2026; recheck model releases and licenses when installing.
