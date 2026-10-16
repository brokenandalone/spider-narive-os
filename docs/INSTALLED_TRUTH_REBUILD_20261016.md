# Spider OS: installed-truth rebuild (2026-10-16)

## Authority and safety
This is a **new source-integration branch**, not a new installation of Spider OS and not a claim that the PC has been mirrored. It begins at `feature/spider-software-art-lab-20261016` to preserve Audio Studio's Wave 9 foundation and the native Art Lab work. The running Spider OS PC is the authority for known-good behavior.

**Do not merge, install, flash, update boot partitions, overwrite the resident Webbie, push private files, or run a release installer from this branch before the installed-source audit and owner review.** Never publish microphone samples, authentication material, token files, local Ollama memories, private case files, manuscripts, artwork, music, OneDrive data, or operational station data.

## Known working state supplied by the owner
- Ubuntu Studio 26.04.1 with LUKS-on-LVM `kali-vg-root`. The current PC boot mode, partitions and bootloader configuration are **not established by this source audit**. Preserve them exactly; do not touch disks, boot entries, or encryption.
- Webbie runs as a **user** service under `spider`, not root. Previous root system service is inactive.
- Webbie AI worker V2 successful end-to-end text/IPC test: `qwen3:8b`, 18 messages, 7,743 prompt characters, 256 generation-token setting, 6.73 seconds; voice heard and spoken reply was **Natasha**. Treat that installed state as protected.
- Webbie's installed agent is larger/different from the GitHub versions. GitHub **must not** clobber owner customizations.
- `webbie-wait-ollama` previously contained unbounded chat startup check; owner's fix used a bounded availability check.
- Kali Bay rootless Podman container `kali-bay` running, with Suricata and auditd previously verified. Never give unrestricted root commands to generated AI text.
- Author, Study, Studio/Audio Studio, Media/Nova/BCN, Art Lab, Forage, Deep Forage, The Web and existing native bays should remain real working applications, not replaced by launcher mockups.
- Installed music, author source, creative assets, private evidence/case files, credentials, and unique configurations remain on the PC. A public GitHub repository is **not** the place to upload them.

## Reconcile before building
1. Keep using the **known-good installed** Spider OS. Do not run any new installers.
2. Clone this branch into a **separate folder** from the existing source checkout.
3. Run `python3 tools/spider_installed_truth.py --repo . --output ~/Downloads/Spider_OS_Installed_Truth` on the PC. It is read-only except for writing the local report. It does **not** upload files.
4. Review `SUMMARY.md` for `identical`, `different`, `installed_only`, and `repo_only` source paths.
5. Reconcile only reviewed code, one subsystem at a time, preserving installed originals. Keep private materials out of the public repository.
6. Run existing source checks, user-service/voice/AI regression tests, native bay tests, Kali access tests, and the unified release preflight before any installation or release.
7. Only after owner review of the installation diff use a **single coordinated upgrade transaction** with backup and rollback.

## Snapshot scope and limitations
The comparison inventories source-like files under `/usr/local/lib/spider-os` and compares them against Git-tracked files in this checkout, using SHA-256. It separately records *filenames and hashes only* for a small number of owner-relevant service/config paths. Symlinks are never followed; caches and personal data are excluded. It does not copy code, read home documents, read secrets, modify services, perform a backup, or prove that a release boots. A filesystem snapshot cannot establish running behavior; the PC's working Webbie/Natasha and native workspace checks must be repeated in real use.

## Current status
GitHub branch **created**. GitHub source is **not yet reconciled** with the PC. No install, PR merge, or ISO release is authorized by this branch.

## First live source inventory (owner-reported, 2026-10-16)
The initial local read-only audit at Git commit `c87786e163be27f1a26890b854b8859abcbe1df3` reported: **313 identical, 39 different, 508 installed-only, 249 GitHub-only**.

This is **not** proof of 508 missing programs. The installed-only set includes at least 74 `upgrade-backups/` paths and eight `webbie.backup-20261003-040101/` paths; the 422 `webbie/` paths need closer triage. GitHub-only includes 199 tests and 28 `distro` paths (expected build-side files rather than necessarily missing PC programs).

The changed-file subsystem counts were: the-web=13, webbie=9, author=4, forage=3, kali-bay=3, media=2, studio=2, study=2, system=1. These represent **owner-installed code that must be reviewed**, not something to overwrite with existing Git source.

To inspect the *existing* local report without rescanning or transferring files:

```bash
cd ~/Downloads/Spider_OS_Installed_Truth_Rebuild
git pull --ff-only
python3 tools/installed_truth_triage.py --limit 35
```

The classification tool only reads `~/Downloads/Spider_OS_Installed_Truth/manifest.json`, prints candidate live code separated from likely backups and development assets, and makes **no filesystem or GitHub changes**. Do not upload the manifest or private owner source to this **public** GitHub repository. Reconcile reviewed, non-sensitive source only.
