# Spider OS October 12, 2026 | ALL Upgrades, ONE Coordinated Release Window

**Audit snapshot only. Do not install from this branch. No files on the owner PC have changed.**

## Why this exists

The native Spider OS nightly sources contain many nested feature branches and PRs.
Other work happened concurrently in the Media Center, BCN website, Nova and a
legacy Spider OS1 mirror. A green CI run on Wave Six covers its exact commit,
not changes merged into another repository afterward. *Do not assume a PR is
installed merely because it is merged into its repository.*

The complete, machine-readable audit is:
`docs/releases/2026-10-12-master-cross-repo-inventory.json`

At capture time the linked repositories showed:
- **Native Spider OS (`spider-narive-os`): 94 open PRs.** These include old
  stacked ancestors and alternative designs. **Do not merge or install 94
  times**. Classify every pending PR as already inherited, superseded,
  still wanted, incompatible, or needing integration; reconcile overlapping
  entrypoints once.
- **Spider-OS1 legacy mirror: 9 open PRs.** Source reference only. Not a
  second OS installation or an authorization to touch the bootloader.
- **Spider Media Center: 2 open PRs.** PR #11 bounded radio shutdown and
  PR #23 new Nova Australian voice-selector / library cleanup / cue rotation.
  The V7 playlist workshop and all-four-artist show generator (PRs #21 and
  #22) are already merged into Media Center main, but PC installation remains
  unverified.
- **BCN website: 1 open draft PR (#14)** for dedicated Broken World pages.
  BCN v3–v15 updates including latest Command Center work are merged into
  BCN main, but production deployment and end-to-end admin checks remain
  separate.
- **Nova shared voices (native Spider OS PR #102)** merged to Spider OS main,
  **AFTER** the previous Wave Six SHA was frozen. The new
  `media/ai-dj/nova_voice.py` module is absent from that exact Wave Six
  candidate. The new PR's `media/ai-dj/service.py` changes overlap the
  owner's customized live Nova service. Preserve live behavior and explicitly
  reconcile voice selection. Do not silently copy an older service over it.
- **Matilda fallback docs (native PR #100)** remains open; review before
  final release, and preserve the user's installed voice preference.

## Three deployment targets in one coordinated session

1. **Native Spider OS local batch**: The Web, Webbie, Qwen3 8B selector,
   resident voice/microphone/STOP, Nova server integration, Study, Author,
   Studio, Forage, Deep Forage, Kali Bay and desktop. Preserve the uploaded
   31 customized installed source files and their semantics. Use one local
   release candidate and one guarded OS installer with a single backup/
   rollback receipt. No model pull, bootloader rewrite, credential migration,
   hidden camera capture or unconditional privileged automation.
2. **Spider Media Center app**: separate V7 application installer plus Nova
   radio bridge validation. The entire merged playlist workshop and BCN
   generation workflow must be present; integrate approved PR #23 if desired.
   Validate actual bulk selection, playlist saving, radio shows, only the
   four approved artists including J-Cold, user playback, fullscreen GPU
   visualizer and actual Nova voice/audio rather than HTTP health alone.
3. **BCN website/server**: separate deploy from `bcn-network`. Verify
   visitor/owner access, private admin authorization, public pages,
   artwork/story pages, web backend, live station status and rollback.
   Review PR #14 rather than assuming its unmerged pages are deployed.

These are **three independent deployment/rollback procedures** coordinated
as ONE owner-visible upgrade window. They are not technically one executable
installer, and success in one must never mask failure in another.

## Freeze and release rules

- Recheck all GitHub repos **immediately before build freeze**; this JSON is
  as-of October 12, not an immutable promise that no later PRs exist.
- Every PR is explicitly classified and cited, including old ancestors,
  competing changes, new main merges and external deploys. Deduplicate
  nested PR histories by commit ancestry and source diff, not by titles.
- Use the user's running PC as the functional baseline. The 31-file
  offline staging process preserving owner bytes is **NOT a completed merge**.
  New entrypoint-only features still need manual integration and interface
  testing. Do not commit personal source/voiceprints to a public repo.
- Confirm `qwen3:8b` remains configured, the owner speaker policy only
  authorizes Cory and Shayna, and emergency STOP works. Verify hearing,
  silence handling, speaker echo, TTS output, Australian voice and
  reactive audio with consent and actual hardware.
- Compare the final combined sources with the owner-provided fingerprints
  immediately before and after apply. No unrecognized overwrite.
- Obtain explicit owner approval of the exact frozen SHA and per-target
  release packages after tests. Confirm full backups, rollback *test* and
  no already-used same-day OS install receipt.
- If a post-freeze PR or local customization arrives, either review it
  and rebuild/test a **new final SHA** or explicitly defer it to a later
  session. Don't quietly drop it. Never wave through unverified code.
- Capture the next known-good state **only after all physical tests pass**.

## Important reality checks

No package is currently approved to install. The all-upgrades ledger is a
scope guard and audit, not a real feature merge, downloadable complete
installer, device-control credential or proof that a service is operational.
The previous CI run passing 1,165 tests validates its own source snapshot,
NOT this newer full release, Media Center, BCN deployment or real PC.
