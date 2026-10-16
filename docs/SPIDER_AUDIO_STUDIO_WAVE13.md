# Spider Audio Studio Wave 13: Import WAVs and PLAY THEM INSIDE Studio

## Why Wave 13 exists
The owner successfully ran Spider Audio Studio Wave 12 and previewed an
original Broken Sorrow guitar piece, but importing four stems previously
required copying a long Konsole Python script, and the Session Mixer could
only open an external audio player after offline rendering.

Wave 13 makes this a practical **in-app song workflow** rather than asking
users to write code merely to import an existing arrangement.

## Native Studio tab: Import WAVs · Create Song
The `studio.main.SpiderStudio` QTabWidget now includes the original
`StemImportPanel` alongside the existing recording, instruments,
arranging, editing, mixing and production modules.

1. Click **Choose WAV tracks** and select up to 24 actual independent
   uncompressed mono/stereo WAV files from the computer.
2. The GUI validates each file and suggests the appropriate recorded role.
   It recognizes Broken Sorrow-style `Rhythm_L`, `Rhythm_R`,
   `Lead`, and `Ambient` filenames; every role has an editable dropdown.
3. Set a song title and BPM (for What the Silence Kept: **96 BPM**).
4. Click **Create New Multitrack Session**. A cancellable QThread uses the
   original protected Studio multitrack exporter, which copies and hashes
   source audio into a NEW private session folder and never modifies originals.
5. Click **Open Session in Spider Mixer** and verify each track, adjust
   gain/pan, insert individual EQ/room/compression, edit clips or drag
   multiple song regions, then **Render non-destructive session mix**.

The importer is not a new system launcher, DAW substitute, audio codec
converter, downloader, or arbitrary directory scanner. It never opens a
microphone and never creates an album or modifies user music tags.

## Actual rendered WAV playback inside the original Session Mixer
`MixPlaybackBar` is embedded in `SessionMixDialog` after the render
controls. Once the mixer finishes creating a private WAV, the owner can
click **Play in Studio**, **Pause**, **Stop**, or seek to a position.
The transport shows elapsed and total playback times.

It uses Qt5 QMediaPlayer for **audio output only**. No voice capture, no
always-on hardware stream and no connection to Nova/BCN. It stops playing
when the mixer closes or starts a new export. When QtMultimedia or the
local playback backend is unavailable, the existing **Listen to last
rendered WAV** button still opens the selected regular WAV in the operating
system's default audio player.

This is deliberate **render-then-listen playback**, not realtime zero-latency
multitrack monitor auditioning; actual low-latency live DSP requires a
separate engine and real USB audio interface evaluation.

## Versioning and automated verification
`studio/package/build_standalone.py` now emits
`Spider-Audio-Studio-0.13.0-dev.tar.gz`, a distinct owner-only preview so
existing 0.11/0.12 files are not confused with the new software.

The GitHub Actions `Spider Audio Studio private source preview` workflow
builds and SHA-256-verifies the application package and publishes a
short-lived downloadable archive.

`tests/test_spider_stem_import_and_transport.py` exercises:
- Role recognition on Broken Sorrow guitar WAV names.
- Validation of independent PCM source tracks and symlink rejection.
- End-to-end four-track guitar WAV session creation and a **real 48 kHz
  24-bit FFmpeg stereo mix** with all originals byte-for-byte preserved.
- Native import table, editable role dropdown, protected session creator,
  existing mixer handoff and original `SpiderStudio` tab integration.
- QtMultimedia audio transport loading, play/pause/stop/position signal
  handling where available, safe WAV loading and fallback behavior.

## Release gates
This is a GitHub **draft source build**. It does not install over existing
Spider OS, record from microphones, restart Nova/BCN, change user music, or
merge other apps. Completing audio-device tests, sample library realism,
live plugin hosting, actual low-latency monitoring and an owner-safe
desktop installation still remains necessary before professional release.
