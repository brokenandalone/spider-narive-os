# Spider Studio v8 Production Workflow: source upgrade

Date: October 11, 2026
Base: Spider Studio v7 Band Mixer; stacked on the October 10 Studio AI source.
Installed PC baseline: **user says the October 10 AI batch is already installed.**

## New Studio features

1. **Private revisioned Band Projects**. Name a song and save all selected WAV file paths, track levels, stereo pan, mute, solo and timing offset. Each save creates a new private revision and leaves older revisions intact. Settings are stored as JSON under `~/Documents/Spider Studio/Music/Band Projects`; audio files are referenced, **not copied**. Projects can be explicitly recalled and missing audio paths are identified. There is no automatic restore at startup.
2. **Solo per track**. Solo a guitar, vocal, bass, drum or piano part; when any solo is checked, non-solo tracks are muted **only for that render**. Source audio and saved user mute checkboxes remain unchanged.
3. **Per-stem start timing in milliseconds**. The new offset range is 0 to 60,000 ms. This is a positive delay, not time stretching, beat tracking, pitch correction or automatic alignment. The FFmpeg filter is `adelay`, with a 48 kHz stereo output. Source tracks are not rewritten.
4. **Audio input audit**. Display WAV duration, sample rate and channel count, with warnings about mismatched durations and resampling needs. Musical sync still needs to be checked by ear.
5. **Existing mix history and audition**. Only previous private `band-*` jobs with valid WAV/receipt files are listed; audition is explicit. There is no cloud sync and no background scan.
6. **DAW multitrack session handoff**. Explicitly seed the existing native Spider Studio multitrack exporter with selected separate WAVs. DAW exports put source WAVs at time zero; the user must reapply offset, pan and gain in the DAW. No stems are generated or silently extracted.
7. **More readable controls**. The Band Mixer presents one labeled band role with a WAV path row, plus a separate level/pan/mute/solo/timing row. No changes to original Studio AI, installed DAWs or Webbie service.

## Safety and integrity

- Only eight recognized mixer roles can be persisted.
- Project files and directory are user-private. Project read rejects symlinks, unexpected paths, malformed or oversized JSON, unsupported schema and invalid mixer control values.
- A new saved revision never overwrites an existing revision. Project files contain no recordings or model weights.
- Separate source files are validated, and audio renders continue to use non-shell FFmpeg with no overwrite flags, per-job private logs and receipts.
- Output receipt now includes `offset_ms` for each independent track. Existing callers with no offsets still default to 0 and remain supported.
- Existing voice models, AI tools, recordings, Studio v6/7 panels and installed Spider OS are untouched by GitHub commits.

## Capabilities not yet implied

The project saver is *not* a native Ardour project with plugins/faders/time line; it stores Spider's mix settings and selected WAV paths. Independent stems still require real recordings or user-reviewed separation. Neither a trained personal singing voice nor Suno-quality generation is proven by these changes. The DAW exporter copies sources at zero offset and does not automatically translate Spider mixing instructions.

## Read-only installed PC comparison

Run from this checked-out GitHub feature branch on the owner PC:

```bash
python3 studio/package/inspect-studio-install.py
```

The report lists which selected Studio source files are missing, different or identical to the installed `/usr/local/lib/spider-os` copy, probes Qt availability and checks FFmpeg's required audio filters. It prints only; it never installs packages, changes services, edits voice models, scans personal audio or overwrites the existing October 10 Studio AI. **Different is not an instruction to overwrite.** Review such files manually first.

## Installation release gates

Before installing onto Spider OS, reconcile these stacked source changes with the **already installed October 10 Studio AI**. Take a backup of the current `/usr/local/lib/spider-os/studio` source and *preserve* all user music, local AI models, training data, Webbie customizations and school files. Run full source/Qt tests and a live PC audio audition; check input/output devices and FFmpeg supported filters; deploy only a reviewed reversible change. Unrecognized PC-local changes block automated replacement.

## Source testing

Unit tests cover offset filtering, source WAV metadata audit, private save and load, malformed project refusal, solo logic, UI worker mapping, DAW export handoff and mix history. Passing CI validates source regressions, **not** on-device capture quality, model performance or audible production standards.
