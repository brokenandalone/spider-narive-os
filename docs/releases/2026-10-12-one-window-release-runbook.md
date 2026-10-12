# Spider OS October 12, 2026 | One NATIVE OS Upgrade Batch Only

**AUDIT/PLAN ONLY. NO INSTALLATION IS APPROVED.**

## Hard project boundary

**This release is exclusively for the native `spider-narive-os` desktop installation.**

- **IN SCOPE:** The Web desktop, Webbie, its Qwen3 8B configuration and
  voice/mic/STOP/owner trust, System and Recovery, Guardian, Study, Author,
  Spider Studio, Forage, Deep Forage, Kali Bay and OS integration services.
- **Native Nova exception:** The `media/ai-dj` Python service *inside*
  `spider-narive-os` is OS-owned integration, and its existing on-PC code
  needs preservation. Native Spider OS PR #102 shared Australian voices
  merged to main after Wave Six was frozen. Review and reconcile this
  **OS service only**, without updating Spider Media Center or BCN.
- **OUT OF SCOPE:** Spider Media Center V7/V6 application and its entire
  GitHub repo, playlists, artist show UI, packaging, updater and independent
  release schedule.
- **OUT OF SCOPE:** BCN Network public website, backend, Command Center,
  story pages, hosting and all deployments.
- **OUT OF SCOPE:** Legacy Spider-OS1 mirror/image installation and
  bootloader or disk repartitioning.

**Media Center and BCN will be handled only in separate project upgrade
sessions. They do not gate or participate in this native OS release.**

The old cross-repository snapshot was preserved strictly as reference at
`docs/references/2026-10-12-independent-projects.json`. It is NOT an
install manifest, test dependency or approval checklist.

## Current native OS situation

Native Spider OS has 94 open PRs at the October 12 audit snapshot, many
of them historical stacked branches and competing designs. They are NOT 94
distinct new installs. Classify and deduplicate the PRs by actual ancestry,
files and retained behavior, then freeze one owner-approved OS source commit.

The owner PC previously reported 31 custom source files which the old
installer refused to overwrite. The offline preservation stage successfully
held each supplied owner file byte-for-byte in a separate review candidate,
but that is *not* a semantic feature merge. New functions wired into
entrypoints still need deliberate integration and tests.

## OS-only release requirements

1. Reconcile all 31 installed source files against the native candidate.
   Preserve locally tested browser, Webbie agent, Whisper/RMS microphone,
   speaker trust, existing desktop menu readability, and owner projects.
2. Keep Webbie's installed **qwen3:8b** model and configured Australian
   voice. Review native PR #102 Nova shared voices only for the
   `spider-narive-os` AI DJ service; never install or alter the
   separate Media Center application as part of this step.
3. Integrate The Web, System, Recovery, Webbie, Study, Author, Studio,
   Kali Bay, Forage and Deep Forage upgrades with source-level and
   behavioral tests. No wholesale replacement of newer installed code.
4. Freeze one native OS Git commit after all desired OS-only changes.
   Run all source CI on **that exact commit**. Confirm the checkout has no
   unexpected modifications and the known-good PC fingerprint still matches.
5. Complete physical tests of user login, desktop workspaces, file/save
   paths, Qwen3 8B chat, wake/STOP, hearing, TTS, approved owner speech,
   security tool authorization and **native Nova OS service**. Passing
   HTTP health or source CI alone cannot validate live audio.
6. Obtain the owner's explicit approval for **one** central native OS
   installation with a verified backup, available recovery process,
   daily install receipt and rollback. No automatic reboot or install.
7. After verifying the installation on the real PC, record a new
   owner-confirmed known-good snapshot.

## Exclusions enforced by the release guard

`tools/release_inventory_guard.py` must reject any OS release inventory
which: includes a separate project in its in-scope repositories; adds
Media Center or BCN approvals/PRs to the OS release gates; fails to name
both external projects as exclusions; or claims a ready/installed status.
The external-project reference does not determine release readiness.

**Release gates remain closed.** The previous 1,165 passing source tests
belong to the earlier owner-preserving staging commit, not this revised
scope or a functional installed OS candidate.


## October 12 source integration progress (still no installation)

The native OS owner ZIP has exactly 31 guarded customized installed source files.

- `tools/owner_source_semantic_audit.py` inventories owner-only APIs,
  candidate-only APIs, changed common implementation ASTs, changed function
  signatures, constructor wiring differences and module imports without
  importing/executing the uploaded owner Python. The JSON contains no
  source code.
- `tools/patch_owner_session_detection.py` creates an owner-hash-pinned
  PRIVATE proposal for the existing `webbie/agent/webbie.py` that fixes
  desktop session detection (do not return early on inactive TTY).
  Firefox/research/microphone/voice callpaths remain unchanged in this patch.
- `media/ai-dj/nova_voice.py` is included from native Spider OS merged
  PR #102 for Australian neural voice availability and validated audio.
  The installed Nova source remains the baseline.
- `tools/patch_owner_nova_voices.py` builds a PRIVATE proposal using the
  real owner `media/ai-dj/service.py` hash and only adding the reviewed
  native voices route / selection / synthesis interface, preserving the
  original on-air backend/host and DJ scheduling methods. It does not
  install or update the separate Spider Media Center.
- `tools/run_private_os_reconciliation.sh` runs all above offline,
  staging the initial 31 byte-for-byte originals, two proposals and a
  metadata report under an owner-private folder. It does **not** copy
  experimental proposals into the installable source.

Run this **only with the exact successfully tested SHA for this branch**,
after cloning/fetching into a fresh detached checkout. The owner archive
must still match the actual installed files:

```bash
bash tools/run_private_os_reconciliation.sh \
  ~/Downloads/Spider_OS_Conflict_Source_Review.zip \
  ~/Downloads/Spider_OS_Full_OS_Review_20261012 \
  <EXACT_40_CHARACTER_CI_VERIFIED_SHA>
```

The third argument is the complete pinned commit, NOT literally the
placeholder. A changed source file, unmatched model, missing helper, or
already-existing review folder blocks staging. No sudo. Do not install or
restart any services from this folder. Upload `semantic-reconciliation.json`
for follow-up owner-safe semantic merge review.

**Progress is limited:** Two specifically reviewed native source proposals
are drafted, *not* deployed or hardware-tested. Remaining conflicts and new
GUI workflows still require manual merge and integration, then a fresh
exact-SHA full source/PC test and approval. CI on the staging script does
not prove all 31 conflicts are resolved or authorize release.
