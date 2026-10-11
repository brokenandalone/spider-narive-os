# Spider Studio v9: Release Desk and mix starting presets

Date: 2026-10-11  
Branch: `feature/studio-release-export-v9-20261011`  
Stack: v8 Studio Projects -> v9 Release Desk

## User's installed baseline

Owner has already installed the October 10 Studio AI work on Spider OS. **No GitHub source action installs or changes that PC.** Preserve the installed source, models, recording sessions, Webbie's customizations, the music collection and personal documents. Any release installation remains a separate backup-first, installed-versus-GitHub reconciliation activity.

## Added in v9

1. **Release Desk tab:** A new tab beside Studio AI and Band Mixer accepts a deliberately selected finished WAV, including explicit handoff of the last rendered Band Mixer WAV.
2. **Three local release exports:** Independent checkboxes for 48 kHz/24-bit stereo PCM studio WAV, 44.1 kHz/16-bit stereo PCM CD-ready format, and 44.1 kHz 320 kbps stereo MP3. MP3 requires that local FFmpeg supports `libmp3lame`; unavailable codecs produce a truthful private-log error, not fabricated audio.
3. **Revisioned release bundles:** Each export makes a fresh user-private `release-*` folder containing chosen outputs and a provenance `release.json` with input SHA-256, profile selection and output byte sizes. No previous files or original recordings are overwritten. Failed and canceled new bundles are discarded.
4. **Audio checks:** Reject symlinks, empty/malformed WAVs and unknown encoder profiles; require actual PCM source, validate WAV output settings and never invoke a shell for FFmpeg. Source byte-level tracking detects a concurrent external source-file change.
5. **Release history:** See completed local export bundles only, and open the bundle with your file manager explicitly.
6. **A/B listening:** Audition two existing Band Mixer WAVs through the local player, one at a time. This is **manual sequential comparison**, not synchronized crossfade or instantaneous blind A/B.
7. **Four explicit starting-point mix recipes:** Neutral, Broken Sorrow two-guitar spread, vocal duet, and sparse haunted piano. These apply level and stereo pan values only, never changing imported source WAVs, mute, solo, offsets, personal voice models or saved revisions. Save as a new project revision to retain.
8. **PC reconciliation:** Existing read-only Studio audit recognizes the three new source modules. A separate PC install is not performed.

## Capability boundaries

The Release Desk performs *format conversion* of an existing finished WAV, not mastering, loudness normalization, audio quality certification, stem separation, real owner voice training or automated DistroKid upload. The word 'CD-compatible' describes the PCM encoding and sample rate, not a professionally approved final master. The '320 kbps' selection refers to an intended encoder setting; final listen/release acceptance is on the owner's PC.

Generated song prompt instructions still do not guarantee real independent guitars or isolated guest singers. The current trained My Voice chain must be separately qualified by authentic user recordings and safe local model setup.

## Verification

Source/Qt unit tests cover profile selection, correct guarded FFmpeg invocation, unique output folders, permission-restricted logs/manifests, immutable source WAV, cleanup on encoder failure, invalid/untrusted receipts, manual release UI and mix comparison, and track-preserving mix recipes. GitHub CI validates Python/source regressions; PC audio acceptance, actual GPU AI quality, recording-device performance, codec support and auditory release quality remain to be established.

## Pre-install inspection

From the v9 checked-out branch, read-only:

```bash
python3 studio/package/inspect-studio-install.py
```

Review every `different_inspect_before_replacing` result against the already-installed October 10 Studio AI. A future combined installer should apply only reviewed changes, preserve model/data directories, take an easy-to-restore backup, and verify actual WAV/MP3 playback and user permissions.
