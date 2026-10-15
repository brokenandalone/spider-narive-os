# Spider Auto Performer: sheet music and tablature playback

Source-stage capability (2026-10-15). Implemented on the feature branch, not yet installed or tested on the owner's actual audio interface.

## User workflow

1. In the **real Spider Audio Studio** select **Auto Performer · Scores & TAB**.
2. Import **MusicXML** (`.musicxml`, `.xml`), **compressed MusicXML** (`.mxl`), or **plain-text standard guitar/bass TAB** (`.txt`). You can also paste standard 6-line guitar or 4-line bass tabs.
3. Review the detected parts, tempo, note count, warnings and duration.
4. Select which part to edit and its **General MIDI instrument patch**. Acoustic/electric guitar variants, bass types, piano, strings and more can be selected without editing the score.
5. Choose a **local SoundFont (.sf2 or .sf3)** with permission to use it. Optional independent **FluidSynth** must be installed separately. Select **Play score automatically**. Spider renders the full performance offline, then sends the resulting stereo PCM WAV to Qt Multimedia for playback on the user's audio device. Playback does not start until clicked.
6. Export the same notes as **multi-part standard MIDI** or a 44.1 kHz stereo WAV via SoundFont. Nothing replaces the source MusicXML/TAB/SoundFont.

## Implemented notation semantics

- MusicXML score-partwise notation: multiple named parts, note pitches, alterations, rests, voices with `backup`/`forward`, chords, explicit note durations, ties, fixed time signature, first tempo, written transposition, and embedded MusicXML General MIDI program choices.
- Drum kit notation: uses actual MusicXML `midi-unpitched` mappings for each unpitched instrument; uses MIDI channel 10 and respects MusicXML's **1-based** MIDI note/program encoding.
- Text TAB: 6-line standard E/B/G/D/A/E guitar or 4-line G/D/A/E bass. Fret 0–24. Simultaneous fret positions become real polyphonic chords. Text TAB has no reliable rhythm by default, so the owner explicitly selects 1, 2, or 4 columns per beat and can select BPM.
- MIDI export: SMF type 1 with distinct instrument tracks, tempo, time signature, program changes, polyphonic note-on/note-off, velocity.
- SoundFont export: separate licensed local file and FluidSynth CLI (no shell), sample rate 44.1/48 kHz, 16-bit stereo WAV, bounded duration, validated output, atomic saving. Nothing automatically downloads third-party sound banks.
- Animated transcription/synchronized note cursor is not yet implemented; the Audio workbench remains playable independently.

## Known limits

This does **not** yet read photographed sheet music, scanned PDFs, lyric/chord sheets, or Guitar Pro's proprietary `.gp3/.gp4/.gp5/.gpx/.gp` binaries. Export MusicXML/MXL from MuseScore or another notation editor first. Repeat barlines are warned about and not expanded. Changes of tempo/time signature, grace notes, trills, slides, hammer-ons, bends, vibrato, picking and realistic strum mechanics need later work. Text TAB rhythm is approximate. Unsupported unmapped drum notes are rejected rather than silently invented.

**Professional instrument quality is not guaranteed solely by choosing a GM patch.** Sound quality is determined by the instrument recording library's licensing, sample depth, round robins, velocity layers and articulations, plus FluidSynth settings and master effects. The initial procedural synth remains available in the other Studio tools. A truly marketable product needs licensed high-resolution multisampled instruments (or a commercially licensed compatible engine), advanced expression controls, low-latency device support, humanized score playback and empirical audio QA.

The first fully featured release must provide non-destructive sheet-to-notation conversion for scanned PDFs/photos, extended TAB formats, tempo maps, MIDI 2.0 or CC expression where applicable, and an open source/commercial licensing audit. Do not market as fully automatic transcriber yet.

## Licensing

FluidSynth is LGPL; bundling or dynamically linking is subject to its license obligations. SoundFonts are independent works whose reuse, redistribution and commercial terms must be checked **individually**. The rest of Spider Audio Studio currently uses PyQt5, which requires GPL-compliant distribution or an appropriate commercial license for proprietary products.

## Installed PC safety

The developer branch and draft PR do not modify the installed 26.04 PC or existing audio stack, Webbie, Nova, Ardour, Audacity or Mixxx. Continue reconciliation of the existing 31 blocked customized files before any safe guarded upgrade. Do not bypass the existing no-overwrite checks.
