# Spider Studio AI: own-voice song generation (owner priority, 2026-10-09)

Status: engineering specification, **not installed functionality**. Developed separately from the currently installed and owner-reconciled release. No downloaded model, training job, camera/microphone activation or paid service is authorized by this document.

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
