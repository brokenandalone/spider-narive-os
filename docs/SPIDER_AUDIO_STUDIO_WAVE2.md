# Spider Audio Studio / production prototype wave two

## What's real in this development branch (not installed on owner's machine)

One **native Spider Studio window** now contains new panels:
1. **Play Instruments**: drum machine, 6-string guitar fretboard, 4-string bass fretboard, 2-octave keys, 16-step note/pattern editor.
2. **Song Arranger & Mixer**: capture patterns, rearrange/duplicate/edit 1-bar sections (32-bar limit), seven channel levels/pans/mutes/solos; JSON song projects, whole-song stereo WAV and seven-track stereo stem export, standard MIDI format-1 export.
3. **Waveform Editor**: inspect one PCM WAV, apply source-preserving trims, fades, gain and reversal; preview and export to a **different** WAV file. Original input stays untouched.
4. **DJ Decks**: two original-PCM decks, static equal-power crossfade, independent volume, preview first five seconds and full-length stereo WAV bounce without affecting Nova.
5. Existing **Studio AI, Band Mixer, release and audio-quality panels, installed application tool listings**, plus all system audio software, are unchanged.

## Honest limitations

This is a functional *source-stage prototype*, NOT a real-time DAW comparable to mature Ardour, Audacity or Mixxx yet. Studio still needs:
- Low-latency PipeWire/JACK backend; glitch testing; audio/MIDI device selection and USB MIDI controller recording.
- Non-destructive multi-track clip timeline, destructive editor undo/redo, multichannel live recording, plugin automation.
- Real drum samples and guitar/bass multisample libraries with legal provenance. Current instruments are original synthesized prototypes, not sampled acoustic instruments.
- A live DJ streaming mixer with beat grids, sync, jog wheels, cue points, latency controls and rights/licensing for radio content. Nova's existing live service is NOT linked to the offline DJ panel.
- Support for high-bit-depth PCM, FLAC/MP3 import under appropriate codec licensing, rate conversion, metering, spectrograms, time-stretching, effects chains and automated crash recovery.
- Hardware, QA, accessibility, offscreen Qt, performance and packaging verification. CI alone is not hardware validation.

## Safe development verification (source folder ONLY)

To inspect only the feature sources in a clean folder, without switching the PC's working checkout or installing into `/usr/local/lib`:

```bash
git clone --depth 1 --single-branch --branch feature/spider-audio-instruments-20261015 \
  https://github.com/brokenandalone/spider-narive-os.git \
  "$HOME/spider-audio-dev"
cd "$HOME/spider-audio-dev"
python3 -m unittest tests.test_spider_instruments_engine tests.test_spider_song_arranger \
  tests.test_spider_waveform_editor tests.test_spider_midi_song_export tests.test_spider_dj_decks
QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_spider_audio_gui
```

The optional native GUI may be run **only in an interactive desktop** as `python3 -m studio.main` when its existing dependencies are satisfied. It currently creates the usual `~/Documents/Spider Studio` folders when started and may check local services; tests above don't interact with audio devices.

This branch intentionally does **not** update installed program files, models, music, websites, bootloader, OS, or Nova. The user's locally customized files previously failed release preflight. Do not bypass the source reconciliation gate to apply this branch.

## Product and rights gate

The repository MIT license covers original Spider source only. PyQt5 is GPL/commercial licensed; the licenses and patent/royalty obligations of all future components must be reviewed for how the application will be distributed. Marketable means tested audio quality, stability, rights compliance, installer/update support and user documentation, none of which is complete yet.
