# Spider Audio Studio: Product release gate

## Positioning
Spider Audio Studio is an independent desktop recording and music-production
**application**, not a bay launcher. The Spider OS Studio bay remains an entry
point to that same software. The app currently has a Qt standalone window,
recording, arrangements, editing, DJ decks and other development modules.

## First packaging deliverable
Run from the verified repository checkout:

```bash
python3 tools/build_spider_audio_preview.py --output "$HOME/Downloads/spider-audio-studio-preview.tar.gz"
```

Creates a **source-only developer preview** with a local RUN_PREVIEW.sh
that runs studio/main.py directly without the Spider OS app launcher. It includes
explicit Python/Qt shell dependencies currently imported by Studio and source
licensing, but never owner files, music, SoundFonts, backups, credentials, build
outputs, or private branches. It does not install or overwrite the OS.

This is **not a market-ready installer**. It does not provide dependency locking,
a tested package manager installation, automatic updates, commercial plugin
support, code signing, Windows/macOS distribution, performance qualification,
multi-hour record endurance, real audio hardware calibration, or third-party
sample licensing. Qt/PyQt and FFmpeg distribution/commercial obligations must be
reviewed before redistribution. The repository MIT license alone does not settle
the licenses of bundled or required dependencies and assets.

## Mandatory gates for an external beta
1. Eliminate imports requiring Spider OS's desktop shell and system modules or
   move the necessary non-OS code into a clean common package.
2. Provide install/uninstall packages with dependency manifests and reproduce
   clean-machine startup without Spider OS.
3. Validate recording, overdub, editing, arrangement, export, crash recovery,
   and audio device access on actual target hardware.
4. Validate session migration, safe non-overwrite and recoverable saves.
5. Complete third-party dependency and sample/font license inventory, branding
   clearance, privacy policy and customer-facing documentation.
6. Publish a signed beta only after packaging and end-to-end release tests pass.

The existing PR remains draft; do not install the source bundle over owner's OS.
