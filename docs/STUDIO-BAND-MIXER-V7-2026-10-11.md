# Spider Studio: Band Mixer v7 source upgrade (October 11, 2026)

## Protect the installed October 10 Studio AI

The owner reports that yesterday's Studio AI upgrade is **already installed** on the PC. That installed code, local ACE-Step and RVC models, training audio, customized Webbie services, DAW settings, and song files are the preservation baseline. This GitHub branch does **not** install onto the computer, assume the installed files match GitHub, or run any background engine installation.

Do not replace `/usr/local/lib/spider-os/studio` blindly, and do not merge this stacked feature to main until the desktop/source reconciliation and PC backups have been verified.

## Added here

- The current Studio AI tab remains in place; a distinct **Band Mixer** tab makes actual separate WAV tracks easier to manage.
- Independent roles: instrumental bed, lead/My Voice vocal, guest/female vocal, rhythm guitar, lead guitar, bass, drums, and piano/keys.
- Each included source has a path selector, level from 0 to 2, stereo pan from hard left (-1) to hard right (+1), and mute checkbox.
- Rhythm guitar starts panned modestly left; lead guitar modestly right. These are editable convenience defaults, not a production claim.
- Explicit **Import Studio AI selections** copies existing manually chosen WAV paths and levels into the new mixer when requested. No audio is generated or copied by this control.
- FFmpeg is invoked directly (not through a shell) to render a new 48 kHz stereo WAV. Audio sources are never overwritten. Stop/cancel remains available during rendering.
- The private output folder stores a new WAV, log and JSON receipt listing role, original file, level, pan and mute for each track.
- Duplicate/hardlinked files, symlink inputs, invalid audio, out-of-range pan, nonboolean mute, unknown roles, all-muted mixes, and overwrite attempts are rejected.
- Existing old `mix_band_tracks(..., gains=...)` calls remain valid; pan defaults to center and mute defaults to false.
- Mock-backed unit tests cover controls, validation, output receipts and non-destructive exports.

## Important capability boundaries

This mixer blends genuine isolated files. A generated ACE-Step song **does not automatically** provide independent guitar stems, isolated guest singer stems, accurate singing identity, or Suno-equivalent recording quality. The current separate DAW exporter remains the better option for detailed timeline edits. Models and GPU drivers still need to be tested **on the user's actual PC**.

## Before installing

1. Capture the installed Studio source tree and release markers, Webbie integration, user services and the known working AI panel behavior.
2. Back up Studio source and user-generated music/model files without clearing them.
3. Reconcile this feature with the already-installed October 10 source and all open stacked Studio PRs.
4. Verify `ffmpeg` supports the built-in `stereotools` filter on the PC.
5. Run the source/Qt tests and an actual two-guitar plus lead/guest singer audition on the PC.
6. Offer only a reversible, verified selective upgrade after these checks. Do not overwrite unknown PC-local edits.

## Source verification performed for this branch

- A live Linux FFmpeg command with mono rhythm and lead WAVs, separate stereo balance and gain, and the final 48 kHz PCM stereo WAV output completed successfully in a test environment.
- GitHub-hosted source tests are added, but a passing GitHub Actions run and PC sound audition **must be verified separately**.
