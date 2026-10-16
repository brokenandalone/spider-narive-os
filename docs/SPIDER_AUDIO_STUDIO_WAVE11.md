# Spider Audio Studio Wave 11: Real WAV clip editing + isolated application package

Spider Audio Studio is the **current Spider Software build priority**.
The other Spider-branded apps remain saved in GitHub but are not being extended
until Audio Studio is ready for an owner-approved real-world installation.

## Real native recording timeline editing

The existing **Verified Session Mixing** native dialog now includes **Edit
Selected Recorded Clip · Waveform / Trim / Fade / Place**. This is not a folder
launcher and not a replacement dialog for the mixer. It edits the same
verified, checksum-audited multitrack audio tracks that the owner is mixing.

- A thumbnail reads small, bounded sample windows from the **actual WAV**
  and draws measured amplitude peaks; it never opens the audio interface.
- Source *from* and *until* time picks the portion retained in the final mix.
  The edit uses integer PCM sample-frame boundaries, not a destructive edit.
- Position moves the retained clip up to 20 seconds later in the song using
  the existing output-delay control.
- Independent fade-in and fade-out (up to 30 seconds each) apply to the
  rendered portion. The visible highlight and sloped fade guides update.
- The native session mixer creates one stereo 48 kHz / 24-bit WAV, applying
  clips, EQ, optional compression, room effects, gain, pan, mute, solo and
  one final stereo limiter. The original source WAVs are unchanged.
- Private, file-hash-bound mix presets restore all clip edits and effects;
  older presets with no clip keys load using the original full-length WAV.
- The mixer records each clip and effect choice in the private JSON
  export receipt, with a newly generated output path.
- Mixed audio is bounded to a total 2-hour session and up to 24 tracks;
  trims, fades, placement and source PCM parameters are strictly validated.
  Arbitrary FFmpeg filter expressions and file paths are NOT accepted.

A single source region is currently edited per track. Overlapping multiple
edits within one track, stretch/pitch correction, a full nonlinear clip-lane
editor, automation envelopes and live low-latency effects are NOT implemented
or described as complete. Existing separate two-take comping remains.

## Source-tested product packaging

Spider Audio Studio needs to be software, not a forced full OS replacement.
`studio/package/build_standalone.py` creates a separate, versioned
owner-only **Spider-Audio-Studio-0.11.0-dev.tar.gz** containing the original
`studio.main.SpiderStudio` GUI, its Studio Python modules, minimal system/
workspace imports, the vendored native Workspace MAX backend, and the
Spider Audio icon.

Build from the source checkout, on your own machine:

```bash
python3 studio/package/build_standalone.py --output-dir "$HOME/Downloads"
cd "$HOME/Downloads"
tar -xzf Spider-Audio-Studio-0.11.0-dev.tar.gz
python3 Spider-Audio-Studio-0.11.0-dev/run_spider_audio_studio.py --verify-only
python3 Spider-Audio-Studio-0.11.0-dev/run_spider_audio_studio.py
```

- The launcher verifies SHA-256 checksums of its bundled source before use.
- The package builder refuses existing target paths, symlinked source
  files and oversized projects. Packaging copies **only source/config/art
  files**; it includes no private audio files, SoundFonts, model weights or
  user credentials. The builder never invokes sudo, installs services,
  edits the installed Spider OS, or changes user media.
- Requires system-provided **Python 3, PyQt5, Qt Multimedia** and other
  needed packages already available in the owner's Ubuntu Studio
  environment. **FFmpeg** and **FluidSynth** remain optional local
  backend executables for corresponding features.
- The archive is a private developer source preview, **not** a sealed,
  dependency-complete, signed public binary. Licenses, copyright
  attribution, USB interfaces, MIDI hardware, acoustic fidelity,
  latency, performance and packaging for other operating systems remain
  separate commercial release gates.
- Native Studio remains part of Spider OS; the standalone source preview
  adds another installation-free route to test the same software without
  overwriting the OS's customized files.

## Validation tests

- `tests/test_spider_session_clip_edit.py`: exact source sample-frame
  trim regions, fade bounds, song placement filter graph, corrupt edits,
  real WAV waveform preview (16/24-bit), private preset save/legacy load,
  native Qt dialog, and actual FFmpeg rendered/positioned/faded WAV where
  FFmpeg is installed.
- `tests/test_spider_audio_standalone.py`: bundle completeness, no
  bundled personal music, create-new-only archive, extraction, version
  manifest, SHA-256 verification, actual `studio.main.SpiderStudio`
  import and tamper rejection.
- Existing score, soundbank, capture, overdub, mixing, comping, source
  release coverage, daily source checks and native bay tests remain active.

## Not installed

GitHub CI validates source and a headless Qt runtime, not USB audio
interfaces, live microphone feedback, professional listening or
production-ready commercial distribution. The owner's existing Spider OS
installation has unmerged source differences; no install or restart is
part of these changes. Do not replace owner-customized Studio files.
