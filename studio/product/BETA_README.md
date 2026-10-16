# Spider Audio Studio 0.14 private Linux beta

**Record. Arrange. Mix. Own your sound.**

Spider Audio Studio is an independent native desktop music workspace.
This beta contains the same original Studio application already tested as part
of Spider OS, with virtual instruments, MIDI and score tools, real WAV import,
multitrack sessions, non-destructive clip regions, EQ/compression/room controls,
mix rendering and a rendered-WAV player.

## What this beta can do today

- Import independent mono or stereo PCM WAV files into a new private session.
- Record audio explicitly after choosing a real input device.
- Work with score/MIDI and compatible locally selected SoundFont banks.
- Arrange separate source regions, add fades, pan and channel effects.
- Render non-destructive stereo WAVs and play finished mixes inside the app.
- Reopen verified sessions and private mix presets.

A real instrument/audio interface or compatible sound libraries might be
needed for particular capabilities. This is **not** yet a zero-latency live
DAW, a reliable commercial plugin host or a commercial instrument library.

## Easiest setup: graphical private beta installer

After extracting the downloaded ZIP and inner tar.gz, open the versioned
folder and double-click **START_HERE.sh**, choosing Run if your file manager
asks. Some desktops open scripts in an editor. In that case right-click the
script and select Run in Konsole, or run python3 installer_gui.py.

The Studio beta setup screen offers Check computer, Install for this user
(after explicit acknowledgement), and Run Studio. Nothing is installed,
recorded, shared, or overwritten just by opening the setup screen.

## Linux desktop beta setup (no sudo, no Spider OS replacement)

Requires Python 3, PyQt5 with Qt Widgets, SVG and Qt Multimedia modules.
FFmpeg is needed for offline mix rendering; FluidSynth is optional for
SoundFont-backed instrument workflows. Their absence will be reported by the
doctor and corresponding features may not work.

Download the PRIVATE beta artifact and unpack its inner .tar.gz file. From the
extracted `Spider-Audio-Studio-0.14.0-beta` folder:

```bash
python3 run_spider_audio_studio.py --verify-only
python3 run_spider_audio_studio.py --doctor
python3 install_for_user.py --check
python3 install_for_user.py --install
```

The installer creates a **version-specific** application launcher in your
desktop menu, stored exclusively inside your own home directory. It refuses
to replace an existing installation. You may also skip installation and
launch the app directly:

```bash
python3 run_spider_audio_studio.py
```

No login or internet connection is required for the core local WAV-editing
workflow. Optional music-generation tools may need separately installed
local engines. No microphone activates automatically.

## Your songs, your files

No source WAV is overwritten by the session importer or verified mixer.
Studio makes new private session copies and creates new mix exports. The beta
installer does not collect audio, ask for credentials, register system services,
overwrite Spider OS or connect to the BCN radio station.

Before trying the beta with irreplaceable recordings, retain independent
backups. This beta has not yet completed all hardware qualification.

## Not yet a public commercial release

This is a **PRIVATE TEST BUILD**, not an approved product for sale or public
distribution. The repository's MIT notice does not override licenses for
PyQt5, Qt, FFmpeg, sound libraries or third-party components. Review
`THIRD_PARTY_NOTICE.md` and release-blocking evidence before distribution.

We have not announced pricing, terms of sale, warranties, support promises,
certified operating systems, or plugin compatibility. Those require actual
owner approval, testing and legal review.
