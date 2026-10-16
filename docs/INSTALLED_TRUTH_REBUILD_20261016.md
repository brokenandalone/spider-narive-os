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

## Owner's second local triage (2026-10-16)

The installed-only subset was confirmed from the printed local report:
- 408 modules beneath `webbie/vendor/numpy/` and nine beneath `webbie/vendor/sherpa_onnx/`, which are third-party dependencies, **not native Spider OS features to copy**.
- 82 old backup paths.
- One local install receipt.
- **Eight candidate owner-installed source files**:
  `branding/apply-spider-branding.sh`, `studio/studio.py`,
  `system/daily_install_policy.py`,
  `webbie/agent/webbie_ai_isolation.py`,
  `webbie/agent/webbie_ai_worker.py`,
  `webbie/agent/webbie_brain_primary.py`,
  `webbie/agent/webbie_ops.py`,
  `webbie/voice/speaker_gate.py`.

The modified active code consists of **39 source files** distributed across The Web,
Webbie, Author, Forage, Kali Bay, Nova, Studio, Study and the release system.
These 39 + 8, not the entire 508, are the working-source reconciliation queue.

### Stage exact installed source in the separate clone, NOT on the OS

**This repository is PUBLIC**. Review any staged source carefully for secrets, personal
paths, private media and license restrictions before committing or pushing.
The automated credential scan is incomplete and does not make public publication safe.

The existing local audit hashes remain valid for this step even though GitHub's
reconciliation docs and tests have moved forward, because the source staging tool
validates *each source file* against the original hashes individually.

```bash
cd ~/Downloads/Spider_OS_Installed_Truth_Rebuild
git pull --ff-only
python3 tools/stage_installed_source.py             # verification-only dry run
python3 tools/stage_installed_source.py --apply     # ONLY if the dry run validates
git diff --stat
git status --short
git diff --check
```

The `--apply` option copies only the 39 modified and eight explicitly permitted
owner source paths to the **separate Git checkout**. It does not change
`/usr/local/lib/spider-os`, restart a service, install packages, affect disks,
or make any Git commits or pushes. Source files are not uploaded. If any original
file hash differs from the audit, the checker fails *before writing any file*.
The checkout must be clean and on this exact rebuild branch.

Do not blindly `git add -A && git push`. This is a code review stage, not a
release or public source approval. GitHub-only Art Lab and packaging files are
left untouched. All source remains in the PC's installed form until a later,
separately reviewed release is produced.

## Assemble private review input (after the local 47-file overlay)

GitHub has **not** received the installed source yet. To enable actual source
reconciliation without blindly publishing the owner PC's source, keep the 47
files modified/untracked in the separate checkout, then run:

```bash
cd ~/Downloads/Spider_OS_Installed_Truth_Rebuild
git pull --ff-only
python3 -m unittest discover -s tests -p 'test_prepare_installed_review.py' -v
python3 tools/prepare_installed_review.py
```

The resulting `~/Downloads/Spider_OS_Owner_Source_Review_20261016.zip` contains
the exact installed code **diff patch** and eight additional source files.
It is generated outside Git checkout with user-only permissions; no Git commit,
push, network transfer, services, or installed files are touched.

**Private until reviewed.** An automated scan of known token formats is NOT
complete. Inspect the ZIP and its contents for embedded credentials and private
information before sharing. It can be attached to this ChatGPT conversation for
code review instead of uploading to the public GitHub repository.

A strong red flag in the owner-reported diff is that GitHub has substantial
extra work in `webbie/actions/task_grants.py`,
`the-web/shell/webbie_panel.py`, `studio/main.py`, and
`forage/deep-forage/deep_forage.py` relative to what is currently installed.
Do **not** merge the PC overlay wholesale. Review changed symbols,
interfaces, tests, and live runtime behavior, then integrate differences in
component-specific commits after code review.

## Actual owner-source integration round 1: Webbie AI V2 (2026-10-16)

A source-review archive matching SHA-256
`0b10f3dec0d1ed69445550093a61c7c50dfdc600fcbe14fbb59ef888e5e0cb7c`
was supplied privately in conversation. It contains 39 Git patch targets and eight
additional owner source modules, totalling 10 ZIP entries. The **private review
archive itself has not been committed to this public repository**.

**Merged into this development branch:**

- `webbie/agent/webbie_ai_isolation.py`: existing owner-tested bounded process IPC,
  refined to forward the newer source tree's `advisory_context` argument and
  reject a symlink at the log destination.
- `webbie/agent/webbie_ai_worker.py`: existing V2 full-brain-first model worker,
  bounded local Qwen3 8B fallback; passes workspace advisory context into primary.
- `webbie/agent/webbie_brain_primary.py`: original full-memory brain worker,
  preserving its original `respond(..., advisory_context=...)` contract.
- `webbie/agent/webbie.py`: **only** switches the AI reply import. Keeps GitHub's
  owner speaker verification, interrupted speech/STOP semantics, browser permission
  checks, guarded desktop actions, model status handling and atomic privacy-aware
  runtime state.
- `webbie/config/default.json`, `webbie/brain/brain.py`: select the owner's
  verified `qwen3:8b` model, preserving Natasha, the Author/Study/Studio address
  settings, privacy, proactive monitor and speaker-verification configuration.
- `system/release_batch.py`: explicitly includes all three new worker modules
  in the guarded release inventory. There is **no installer execution**.
- `tests/test_webbie_ai_v2_reconciliation.py` and the dedicated GitHub source
  workflow provide regression checks for these preserved interfaces.

**Explicitly rejected wholesale replacement** from the installed patch:

- Installed `webbie/agent/webbie.py` removes the newer GitHub voice trust,
  cancellation, privacy-aware state and additional authorization flows.
- Installed `webbie/config/default.json` omits GitHub's explicit speaker
  verification and proactive settings. Only the owner's local 8B model selection
  is ported.
- Installed `webbie/voice/speaker_gate.py` treats incomplete enrollment as
  `"bypass"`; that is **not evidence of an authorized speaker**. This module
  was NOT merged or enabled. Existing GitHub fail-closed trust remains.
- Installed `the-web/shell/main.py` drops newer immersive bays and native
  advanced tabs. Installed `studio/main.py` removes audio-panel and MIDI
  lifecycle protections. Both newer GitHub implementations are retained.
- Other 37 installed changed-source files and five additional owner-source
  modules are still under review. The three worker files are the **only**
  additional installed-source modules merged in this round.

**Validation status:** source and regression test code committed; the newly
merged GitHub code has **not** been live-tested on the owner's PC or verified
to pass hosted CI. A previous installed Webbie V2 full-brain AI text/voice
exchange worked with Natasha in ~6.73 seconds; the merged source has additional
compatibility and safety behavior, so that result must NOT be represented as a
live test of this GitHub build.

This branch is **not ready to install or flash**. Do not replace the
working resident Webbie, destroy newer bay source, automatically merge
the entire owner patch, or push a private archive into a public repo.
