# Spider Audio Studio Wave 16: Saved songs, verified portable backups, safe removal

**October 16, 2026 | 0.16.0-beta | private development release**

The new features extend the **same original native SpiderStudio window**. They
do not replace Spider OS, launch competing apps, connect Webbie/Nova, or
change music files without a user-initiated operation.

## Find your songs again

The original "Start a Song" page now includes **Recent saved songs**.
This opens a bounded, read-only inventory of Studio's own private
Multitrack Sessions directory, displaying the title, recorded track count,
BPM and filesystem modification date. It does not crawl the user's
Documents, OneDrive or music collection. The inventory is explicitly
**not verification**. Opening a selected song always invokes the existing
hash-checking `SessionMixDialog` worker.

The user can still browse an arbitrary stored session folder using the
existing owner-approved file dialog.

## Back up and restore a complete Spider song

The saved-song window offers two explicit actions:

- **Back Up Selected Song**: validates the entire source session with
  Studio's original SHA-256 checker, then creates a NEW private ZIP
  containing `session.json`, independent WAV tracks and supported local
  mix presets. It uses no third-party uploader and no cloud transfer.
- **Restore Song from Backup**: reads a narrowly whitelisted stored-only
  archive, validates the manifest index and every file hash, extracts into
  a new owner-private staging directory, reinspects the source WAVs with
  Studio's real session verifier, and publishes the result as a uniquely
  named new session. Existing songs are never overwritten.

Both file operations run on a QThread so the original Qt UI remains
responsive. Close is blocked while a copy is active to avoid discarding
the owner-selected operation; there is no implied always-on background
activity. The user chooses both backup and restore files.

Hard boundaries: maximum 24 WAV tracks, up to 100 local mix presets, ~8 GiB
session source audio, stored-only ZIP, maximum member/path inventory,
no symlinks, no ZIP traversal, no duplicate entry names, no silent
overwrite, and no arbitrary files added to a backup. Disk space is checked
before extraction. Invalid archives cannot publish a Studio session.

**A backup is not a synchronization or cloud-backup guarantee.** Users
should save another copy outside their recording PC. Keep personal music
and licensing documents private unless expressly shared by the owner.

## Remove only the specified beta version

`remove_beta.py` lists installed beta versions or removes one explicitly
named version. It verifies every packaged application source and license
notice and refuses to remove symlinked files, owner-customized desktop
shortcuts or unexpected files inside the application. Normal Python
`__pycache__` for package sources is handled. Other beta versions, current
Spider OS, session backups, rendered mixes and recordings stay untouched.

The graphical setup includes an explicit **Remove this installed beta**
action with confirmation. Version removal is never automatic.

## Examples

From inside the extracted 0.16 beta directory:

```bash
python3 run_spider_audio_studio.py --verify-only
python3 run_spider_audio_studio.py --doctor
python3 run_spider_audio_studio.py --self-test
python3 installer_gui.py
python3 remove_beta.py --list-versions
# Optional, explicit: python3 remove_beta.py --remove 0.16.0-beta
```

No command in the examples installs or removes software unless the user
explicitly chooses the indicated action.

## Quality checks

- `tests/test_spider_audio_saved_songs.py`:
  real saved guitar sessions, bounded inventory, malformed records,
  symlink exclusion, native selection into the existing mixer.
- `tests/test_spider_audio_session_backup.py`:
  real guitar recording+private mix preset round trip; non-overwrite;
  corrupt checksum, unsafe ZIP filename, and symlink rejection.
- `tests/test_spider_audio_safe_uninstall.py`:
  version-specific verified uninstall, preservation of another version
  and user song, Python caches, modified desktop and user-file refusal,
  and clean installation retry.

The existing mandatory FFmpeg self-test still renders real synthetic
multitrack audio, tests source hash integrity, and checks the
48 kHz/24-bit stereo WAV. Passing it does not certify real USB audio
latency, devices, proprietary plugins, or commercial distribution.

## Commercial gating remains

The public sale gate remains **BLOCKED** pending PyQt/Qt/FFmpeg licensing,
third-party asset rights, real-world audio/MIDI QA, privacy/support terms,
software distribution review, and explicit owner approval.
