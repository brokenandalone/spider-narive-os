# Spider OS native bays: approved vision and researched integration targets

**Research date:** 2026-10-16. **Branch:** `feature/native-monster-bays-20261015`. **Scope:** Operating system, The Web, real existing native bays and their integrations. Spider Audio Studio engine, resident Webbie model/voice development, Nova DJ creative development, Broken World website hosting, and Spider OS Mobile firmware development are maintained in their respective projects. This document addresses only their integration points.

**Status:** Planning and source inspection, NOT a release, permission grant, live-hardware validation, or package-install instruction. No owner's private staged source has been included.

## Non-negotiable user decisions already agreed

1. ONE Spider OS and the actual installed The Web desktop; enhance the existing program, never replace it with new launchers/control centers.
2. A native bay is a functioning workspace. Merge features previously demonstrated in launcher/MAX/universal variants into that same bay; do not invent alternate versions.
3. ONE resident Webbie reachable from every bay, shared identity/voice/memory/state and a single STOP/consent authority. No duplicate Webbie service or interface hierarchy; Nova remains the approved on-air persona linked through Media.
4. Preserve **all** Ubuntu Studio apps and host packages, all personal projects, studio assets, manuscripts, music, Kali environment, authorization choices, legacy KDE fallback, and custom wallpapers/SVG where supported. An optional installed-app browser is not a substitute for workspace functions.
5. Cinematic purple/violet-black Spider visual identity, real interactions and immersive 3D, without claiming a decorative canvas is the finished experience.
6. Same GitHub development build, owner-only review of modified installed files, one checked backup/rollback and install transaction; no unverified 26.10 boot changes or surprise restarts.
7. Professional environments: recording Studio; atmospheric Author with interactive Broken City; futuristic Study; cybersecurity Kali; cinema/BCN Media; resident Webbie; evidence-rich Deep Forage; creative Art Lab; and Home, Communications, Productivity, Devices, Dev, Forage, System/Recovery.

## Existing source that must be upgraded rather than duplicated

Inspected in the native-monster-bays development branch on 2026-10-16:
- `the-web/shell/home_dashboard.py`: native Home overview of bays, installed program categorization and missions.
- `the-web/shell/bay_missions.py`: one local mission store across existing bays; user-entered task/state references.
- `the-web/shell/native_utility_bays.py`: Devices, Productivity, Communications, Art Lab, Dev Bay native panels. Devices currently has kernel inventory; Productivity shares missions.
- `the-web/shell/art_workbench.py`: basic drawing canvas and outline processing, not yet a complete professional art environment.
- `the-web/shell/immersive_bays.py`: animated bay canvases and an Author point-map with Apartment 17, Mercer & Ninth, City Hall, Platform Six, House of Echoes. **This is not yet a true navigable 3D Broken World.**
- `system/release_batch.py`: single-transaction source release gate, fails closed on owner customizations.
- `docs/NATIVE_MONSTER_BAYS_20261015.md`: 174 owner-reported app menu entries preserved in inventory, 4,360 installed packages previously audited. Counts are prior host observations, **not** a fresh post-install audit.
- Existing private review reported 34 blocked customized release paths and 15 candidate additions on Oct 16; other documents still mention 33. **Re-run the live preflight after any source changes.**

No inspection of these source files establishes that the user's currently running installed OS contains the candidate additions.

## Research-backed integration targets by native bay

| Native surface | Agreed user goal | Integrate into existing code | Evidence / release gates |
|---|---|---|---|
| **The Web / Home** | Native immersive desktop and one mission control | KWin workspace scripting, KDE Activities/window grouping, real task history, launcher-free bay navigation, drag/drop file handoff, restore sessions, global settings and notifications | Validate against KDE session and X11/Wayland; keyboard navigation, multi-monitor; no replacement shell/service |
| **System / Guardian / Vault / Recovery** | Service health, upgrades, backups, rollback, safe maintenance | systemd status/timers, KDE System Monitor metrics, Kup or restic verification, restore rehearsals, update health; optional read-only Spider Eye status | Never touch encryption/bootloader or copy user keys; verify backup integrity and rollbacks |
| **Devices** | Manage real cameras, microphones, audio interfaces, peripherals, connectivity, tablet | Existing /sys inventory plus UPower, NetworkManager, BlueZ, KDE Connect, explicit pair/unpair/transfer controls; camera privacy state; Spider Eye observation status | Hardware permission prompts; no unconsented capture or destructive disk writes; SM-T290 native OS firmware is a separate project |
| **Communications** | Accounts, inboxes, messages, calendar and notifications in one bay | Kontact/KOrganizer, existing mail/browser integrations, optional Matrix/Element as an existing app, calendar tasks and drafts; Firefox Native Messaging if owner-approved | No duplicate mail database; authentication scoped to account; send is an explicit action |
| **Productivity** | One cross-bay project board | Expand existing MissionStore with dependencies, due dates, source links, activity log, project handoff and daily briefing | No second task store; respect project privacy |
| **Studio (integration ONLY)** | Real professional recording room, equipment, session handoff | Embed controls/status for existing Spider Audio Studio, Ardour, JACK/PipeWire, Carla, installed MIDI/effects and project library; do not code another DAW here | Verify existing audio paths and real recording before claiming feature; separate Audio Studio implementation |
| **Author / Broken World** | Writing environment plus immersive city | Existing chapter/canon tools, manuscript search and revision, named character/scene artwork, verified Broken City map, Blender glTF assets rendered in compatible Qt 3D or selected engine; export via Pandoc | Preserve canon, private assets, source chapters; no imaginary neighborhoods or premature 3D claims |
| **Study** | Futuristic learning/citation system | Course/rubric dashboard, OneDrive document access, Zotero local API / LibreOffice citations, APA checker, offline document text search, teaching/review workflow | Consent to account linking; no sync overwrite; preserve notes and feedback |
| **Forage / Deep Forage** | Genuine source-driven research, evidence relationships | One document index backed initially by SQLite FTS5; provenance/citations, comparisons, saved sources, knowledge graph, full-text ingestion where approved | Separate source evidence from inference, avoid private-file traversal without scope; no unnecessary vector DB service |
| **Kali Bay** | Native cyber operations with defensive/forensic labs | Integrate existing rootless Podman Kali environment, open only authorized tools, Wireshark, OWASP ZAP and optional Greenbone reports, evidence ledger, saved repeatable authorized test plans | Kali remains isolated; no unrestricted host root, blind scans or autonomous offensive activity |
| **Media Center / Nova / BCN** | Immersive theater and radio/media management | Existing broadcaster status, Liquidsoap/Icecast health, Nova schedule/program queue, music catalog and playback, FFmpeg decoder preflight; optional Jellyfin library browsing after cost review | Preserve active broadcast and music metadata; do not restart station during UI work |
| **Art Lab** | Real creation, edit, painting and image pipeline | Existing drawing/outline tools + open real installed Krita, GIMP, Inkscape, Blender and Kdenlive with project-specific handoff; asset library, versioning and export | Never recreate missing Broken World album art or overwrite originals |
| **Dev Bay** | Build, test, package and validate OS/software | Existing read-only git tools, CI checks, test reports, dependency/build truth, PR review, reproducible install manifests | Keep owner-private code off public GitHub; do not auto-apply privileged steps |
| **Webbie bay (integration ONLY)** | Same Webbie embedded into the entire OS | Show and interact with the *existing* resident service, read-only capability/state summaries, in-bay context/handoff, permission-aware Spider Eye status, one STOP | No new model/voice/agent service here; independent Webbie development belongs to its project |
| **Spider Eye (System/Devices integration)** | Ultimately replace God's Eye after parity proven | Desktop accessibility via AT-SPI2, consented PipeWire/portal screen capture, app/window metadata, user-visible permission and evidence log | Preserve God’s Eye until actual feature parity, rollback and consent testing |

## Important fresh 2026 platform findings

- **Ubuntu 26.10 released October 15, 2026**, with nine months of support through July 2027. Keep installed Ubuntu Studio 26.04.1 LTS safe and test first: https://documentation.ubuntu.com/release-notes/26.10/
- **Plasma 6.8 released October 14, 2026**, and retires KDE Plasma **X11 sessions**. Individual legacy X11 apps continue via XWayland. **Plasma 6.8 is the owner-approved TARGET, not the installed version.** Verify The Web's Qt5/X11-specific window and capture techniques on Wayland **before** adopting Plasma 6.8. KDE's new Union styling is still beta, so test theme parity before enabling: https://kde.org/announcements/plasma/6/6.8.0/
- KWin offers supported window scripting: https://develop.kde.org/docs/plasma/kwin/
- KDE desktop scripting exposes Activities and panel control: https://develop.kde.org/docs/plasma/scripting/api/
- Qt Quick 3D supports mixing Qt Quick 2D and 3D content, but the current **PyQt5** The Web shell cannot simply import a Qt6/PySide6 UI in the same running process as a drop-in widget. First test a compatible rendering strategy and GPU overhead: https://doc.qt.io/qt-6/qtquick3d-index.html
- XDG ScreenCast portals mediate display capture and can manage consent/persistence; AT-SPI2 provides semantics for accessible applications: https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html and https://www.freedesktop.org/wiki/Accessibility/AT-SPI2/
- KDE Connect can integrate devices and files: https://apps.kde.org/kdeconnect/
- SQLite FTS5 has ranked full-text search without a separately operated DB service: https://sqlite.org/fts5.html
- Zotero local API supports offline lookup with explicit user enablement and write authorization: https://www.zotero.org/support/dev/web_api/v3/local_api
- Existing-source Podman rootless isolation: https://docs.podman.io/en/latest/markdown/podman.1.html
- Liquidsoap streaming chain: https://liquidsoap.readthedocs.io/en/latest/content/quick_start.html
- KOrganizer account-backed calendar and task features: https://kontact.kde.org/components/korganizer/
- Blender glTF exporter and Krita automation: https://docs.blender.org/api/dev/bpy.ops.export_scene.html and https://docs.krita.org/en/user_manual/python_scripting.html
- Restic verifiable backups: https://restic.readthedocs.io/en/stable/index.html
- For OneDrive, MS Graph delta supports change tracking; **rclone bisync can cause data loss if used incorrectly**. Treat read-only status or one-way copy as first integration, not immediate automated two-way sync: https://learn.microsoft.com/graph/api/driveitem-delta and https://rclone.org/bisync/

## Priority and definition of done

**P0: Release safety and compatibility.** Reconcile current installed owner-specific code against source, fix missing dependencies, audit all services and KDE/X11/Wayland compatibility; never approve install from source-only checks. Test rollback/recovery and preserve all Ubuntu Studio programs.

**P1: Finish functionality already present.** One Home with live services/mission state; real author manuscript and canon tools; real Study course and file/citation flow; real Kali lab operations; Media radio/playback and metadata; Art Lab editing handoff; Devices management; Productivity and Communications. Eliminate dependence on old MAX/Universal launchers while preserving specialized installed applications.

**P2: Deep functionality without service bloat.** Shared optional search, project files and evidence, connections, creative asset library, device sync, previews and audits.

**P3: Production immersion.** Consistent original purple cinematic bay visuals, interactive Godot/Qt-compatible 3D scene where technically sustainable, performance budgets for HDD/CPU graphics, visual accessibility, offline fallback, tested target hardware. Do not pretend current 2D canvases are completed 3D bays.

**Done means:** native bay starts from the real Web desktop; feature actually works against the correct local files/service; preserves previous functionality; keyboard/mouse and multi-monitor tested; untrusted inputs/permissions controlled; installs once, with backup and rollback; owner checks on running machine. The development PR stays draft until all blocked owner files are reviewed and acceptance checks pass.

## Newly recommended tools versus user approvals

**Already approved:** One integrated Web, original bay purposes, immersive visual direction, original projects and applications preserved, private owner review, consolidated install, Spider Eye eventually replacing God's Eye, and the Webbie/Nova integration boundary.

**Fresh recommendations requiring compatibility verification, not yet claimed as installed or approved:** KDE 6.8 / Wayland migration work, Qt Quick 3D, AT-SPI2/portals for Spider Eye, SQLite FTS5 unification, Zotero, Restic, Kup, Jellyfin, Element, additional scanning/reporting tools. Choosing a technology does not authorize installation, credential access, account pairing, device capture, or changes to external services.

## Implemented: choose the best ideas without replacing the operating system (October 16)

The existing Dev Bay now has **Show best ideas for Spider OS**. It reads the one reviewed catalog in `the-web/shell/native_feature_adoption.py` and ranks options by owner benefit, engineering effort and integration risk. This is an **in-bay read-only report**, not an additional launcher, Webbie or update service.

**One repeatable method, for each approved improvement:**

1. **Select:** Identify a feature already requested or explicitly recommended, then attach an upstream source and the correct existing bay.
2. **Prefer reuse:** Choose Spider OS source changes or stable, supported desktop APIs first. Reject a second launcher, another AI instance, or a duplicate application when an existing bay can own the capability.
3. **Rank:** Evaluate benefit (1–5), effort (1–5), risk (1–5), re-use of existing code and dependency mode. Best value goes first, **not** newest version first.
4. **Prototype privately:** Isolated experiments for major 3D/UI/API transitions; do not mix Ubuntu 26.10 or Plasma 6.8 packages directly into 26.04's normal APT sources.
5. **Prove compatibility:** Require source compatibility, native-bay workflow, regression tests, owner-customization reconciliation, tested backup/rollback and real installed-host acceptance. Special changes add mandatory gates (e.g., Wayland for KDE 6.8, boot and independent backup for 26.10, explicit screen-capture permission).
6. **Merge once:** Implement successful work in the **same existing Spider OS branch and original native bay**. No competing assistant, shell or launch program.
7. **Release through the existing installer only:** The catalog never approves or performs installs, even if all its review gates are marked. Existing release preflight remains authoritative.
8. **Validate after installation:** Verify actual project/file/audio/camera/window/service behavior, preserve a rollback path, and mark complete only after hardware-level acceptance.

**Practical access after a separately approved release:** Open **Dev Bay → Show best ideas for Spider OS**. In a source checkout, `python3 the-web/shell/native_feature_adoption.py` produces the same static report. The report does not inspect the installed system, establish real gate completion or certify that a migration is safe.

**Specific direction for 26.10 / Plasma 6.8:** Adopt well-supported API-level features and native-bay changes first. Keep the **Ubuntu Studio 26.10 migration on HOLD** while boot synchronization, independent backups, verified restore, official upgrader availability and host acceptance are unresolved. Plasma 6.8 is the TARGET, not installed. Its adoption needs real Wayland compatibility testing and supported distribution packages before a runtime switch. Installing all newer binaries is **not** a shortcut.

## Cross-distro feature adoption: best of 26.10 and beyond (owner correction October 16)

**Ground truth: Plasma 6.8 is a GOAL, not Spider OS's installed Plasma version.**
The installed Spider OS is still based on Ubuntu Studio 26.04.1 LTS
(owner-reported), with custom The Web/X11 source. The separate Ubuntu Studio
26.10 release migration remains **HOLD** because of the active `/dev/sda1`
boot arrangement and unverified full independent backup/restore.

**Never install foreign distro repositories or mix Fedora RPMs, Arch AUR,
openSUSE zypper, NixOS generations, COSMIC compositor binaries or Plasma 6.8
packages into the live Ubuntu Studio 26.04 APT environment.** Borrow their
principles and supported app APIs, then implement them in the same existing
Spider OS and bays.

### Ubuntu Studio 26.10: portable NOW vs future operating-system migration

Official release (2026-10-15):
https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/

| Worth adopting into existing bay | How to adapt without 26.10 upgrade | Verification |
|---|---|---|
| Single-window audio settings, clearer PipeWire quantum controls | System/Studio integration surface the existing WirePlumber/PipeWire state and provide explicitly authorized changes only after preserving routing | Compare working mic/camera/audio chain and active BCN broadcast before and after; **do not touch live station automatically** |
| Per-package selection rather than bundled audio/video/graphics installs | Improve the existing optional installed-tools catalog to show already installed vs compatible optional packages; no removal or automatic installation | Preserve every currently installed Ubuntu Studio package/app |
| Sonic Pi, SuperCollider, SC3 plugins, JNoise | Optional controls/open-existing-program handoff within native Studio (audio engine built in separate Studio thread) | Confirm actual binary availability and permissions; low-latency testing; no duplicate DAW |
| Updated Ardour, Krita, GIMP, Kdenlive, OBS, Audacity | Provide compatible file/project handoffs in existing Studio, Art Lab, Media; do **not** promise their 26.10 binary versions are supported by 26.04 | Check project round-trip and plugin compatibility |
| Ubuntu kernel 7.3, systemd 261, OpenSSL 4, Rust coreutils and KDE Gear refresh | **Compatibility auditing only** in System/Dev Bay; these are distro-level replacements, not source features we can safely cherry-pick | Active sda1 boot/kernel parity, SysV generator removal, legacy PKCS#11 engines and script behavior; normal distribution upgrade later |
| Opt-in local dictation (Myna) in desktop release announcement | Investigate permission-gated dictation handoff in Communications/Study *only if it can use the existing speech path* | No duplicate resident Webbie or always-on microphone |

Official release base (26.10; Linux kernel/systemd/OpenSSL):
https://documentation.ubuntu.com/release-notes/26.10/
Ubuntu 26.10 announcement (opt-in Myna):
https://lists.ubuntu.com/archives/ubuntu-announce/2026-October/000330.html

### Best ideas from other Linux distributions

| Source | Borrow the principle, not the distribution | Existing Spider OS home | Technical limit |
|---|---|---|---|
| **openSUSE Tumbleweed / openQA** | Tested batches of interoperating updates and functional smoke tests | Existing GitHub tests, Dev Bay, System | Tests must exercise real bay/services, not merely green Python imports; https://doc.opensuse.org/documentation/tumbleweed/updating_upgrading_reverting/ |
| **openSUSE transactional-update / Snapper** | Atomic update receipts and documented recovery | Existing release_batch + private backups | Their snapshot implementation relies on Btrfs; Spider's current root is not Btrfs. **Never claim Btrfs snapshots are available.** https://manpages.opensuse.org/Tumbleweed/transactional-update/transactional-update.8.en.html |
| **Fedora Atomic / Kinoite** | Versioned and checksum-verified update, rollback of application/system payload without deleting personal projects | Existing single Spider OS release manifest, rollback | Do **not** install rpm-ostree or rebase Ubuntu to Fedora. https://coreos.github.io/rpm-ostree/administrator-handbook/ |
| **NixOS** | Desired-state inventory, reproducible configs, generations as a design principle | Native apps and services manifests, Dev/System | Do **not** replace Ubuntu package management with NixOS or publish private machine configuration. https://wiki.nixos.org/wiki/Overview_of_the_NixOS_Linux_distribution |
| **Pop!_OS / COSMIC** | Dynamic per-workspace tiling, pinned workspaces, theme design principles | Existing The Web and KDE/KWin window management | Do **not** run a second compositor/desktop. https://system76.com/cosmic |
| **Freedesktop XDG portals** (cross-distro) | User-consented window sharing and Wayland screen awareness | Existing Spider Eye in System/Devices; use existing global STOP | Revocable user consent, PipeWire, desktop portal backend; https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html |

### Execution rule

1. Rank candidate features using the **already implemented** Dev Bay
   `native_feature_adoption.py` report. Distro of origin is research
   provenance, not an install request.
2. Choose the applicable **existing** The Web/bay entry point; no new
   launchers, independent agents, duplicate dashboard, second audio studio.
3. Prefer a source-only change on the installed OS version, then a supported
   API, then an isolated test. Require separate OS migration for
   kernel/Plasma/systemd/OpenSSL changes.
4. Preserve all owner-specific behavior and check that the existing release
   manifest cannot overwrite protected customized installed files.
5. For Plasma 6.8, prove Wayland/KWin/portals/Qt5 compatibility, live-bay
   startup, input/audio status and rollback in a protected test
   environment. Plasma 6.8 is never silently marked as installed.
6. For 26.10, respect the independent backup, active sda1 boot
   synchronization, restore rehearsal, upgrader availability and
   host-acceptance gates in existing PR #115.
7. Only apply after owner-reviewed backup/rollback and **actual installed
   system** validation. A green source-only CI run never suffices.

Implementation updated in the **same existing native-bays branch**:
`the-web/shell/native_feature_adoption.py`, shown from the existing
Dev Bay; `tests/test_native_feature_adoption.py`. These entries are
**proposals and readiness requirements**, not implemented packages, new
applications, Plasma installation, or authorization to modify the
resident desktop.
