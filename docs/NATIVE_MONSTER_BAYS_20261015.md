# Spider OS native bays: monster development wave

**Date:** 2026-10-15  
**Branch:** `feature/native-monster-bays-20261015`  
**Target:** Existing Spider OS running Ubuntu 26.04 LTS  
**Release state:** Development source only. **Not installed**.

## Product rule: a bay is a real workspace, not a program launcher

The Web is the native desktop, KDE is its stable session and fallback,
and all useful controls belong inside the relevant native bay. A launcher
is justified only when it starts a *distinct installed program* with
specialized capability the bay does not reimplement, or when a KDE
fallback is necessary. Launcher entries are **not** a substitute for
Studio, Author, Kali Bay or any other bay.

This wave moves the generic XDG app list out of the main workspace column
and into an explicitly optional **Installed tools** tab. It does not
remove user-created desktop shortcuts without reviewing the live system.
A remaining `.desktop` file in `/usr/share/applications` is a normal
application-menu registration, not an icon placed on the desktop.

## Ubuntu Studio original applications: preservation is mandatory

**Every app already installed on the user's Ubuntu Studio 26.04 machine
stays installed.** Do not run apt autoremove, purge, replace, reinstall,
or delete desktop entries to make a bay look cleaner. The real host inventory,
not a default distro marketing list, is authoritative.

The Web's **Optional installed tools** tab now provides:

- The app's recommended primary native bay, from a specific Ubuntu Studio
  recording/video/graphics/MIDI/software taxonomy.
- Search within the bay **or across all available installed applications**,
  including apps currently assigned to another bay.
- A plain-English reason to use named programs such as Ardour, Carla,
  QjackCtl, OBS Studio, Kdenlive, Krita, GIMP, Blender, LibreOffice,
  Firefox, VLC, Konsole, KDE Connect and Timeshift.
- A user-controlled **Use selected app in this bay** action. Only
  `~/.config/spider-os/app-placement.json` changes; neither the binary nor
  its XDG `.desktop` file is moved or modified.
- A **Restore recommended placement** action, removing the private override
  and reusing the deterministic standard category map.
- Webbie read-only responses to questions such as
  “Which bay has Ardour?” based on actual available desktop applications.

An application-menu entry and an OS package are **not equivalent**.
Some Ubuntu Studio plugins, command-line binaries and non-GUI libraries
have no `.desktop` file, and some user-hidden/desktop-incompatible launchers
must remain hidden. Absence from The Web's app browser does **not** prove
an application was uninstalled. KDE and Ubuntu Studio application menus
remain available as fallback.

Before any future **approved** installation, make a private, read-only
inventory of visible application menu entries on the owner machine:

```bash
git clone --depth 1 --single-branch \
  --branch feature/native-monster-bays-20261015 \
  https://github.com/brokenandalone/spider-narive-os.git \
  "$HOME/spider-os-native-wave"

python3 -B "$HOME/spider-os-native-wave/tools/ubuntu_studio_app_inventory.py" \
  --snapshot "$HOME/spider-studio-apps-before.json" --list
```

After installing a separately qualified release, compare the preserved
snapshot to the actual host (missing entries are reviewed, not assumed
to be uninstalled):

```bash
python3 -B /usr/local/lib/spider-os/tools/ubuntu_studio_app_inventory.py \
  --compare "$HOME/spider-studio-apps-before.json" --list
```

Those commands inspect names, menu IDs and file checksums; they never
execute or remove a program. The live system's 31 customized code files
remain release-blocked until reconciled with backup and rollback.

## Real machine inventory follow-through, October 15

The owner completed the first inventory on their Ubuntu Studio 26.04 host:

- **174 visible, available XDG application-menu entries**.
- Initial native bay counts: Art Lab **23**, Author **1**,
  Communications **4**, Dev Bay **4**, Devices **4**, Forage **1**,
  Media Center **40**, Productivity **6**, Studio **46**, Study **7**,
  System **38**.
- The owner-local baseline file is
  `~/spider-studio-apps-before.json`. Do not commit or overwrite it.
- This is NOT a complete package list: command-line programs, plugin
  libraries, and audio effects may have no XDG menu entry.

The inspected inventory identified **58 real, specific menu IDs** whose
primary bay was ambiguous or incorrect, now covered by a deterministic
routing table and regression tests. In particular:

- **Studio**: both Spider Studio entrypoints, Aeolus, AT1, DGEdit, DIN,
  Fluidsynth, FreeWheeling, JACK Mixer, SooperLooper, JACK session tools,
  instrument tuners, MIDI/music synths, lighting/video production tools,
  Recorder and JACK networking.
- **Media Center / BCN**: Internet DJ Console, FreeShow, OpenLP,
  Kid3 catalog tag editors and the installed Spider Media Center menu
  entry, in addition to existing music and video players.
- **Devices**: ALSA/FFADO hardware mixer and audio interface controls,
  KDE device utilities, Wacom tablet locator and QR camera tool.
- **Webbie**: the resident assistant, her face wake/sleep actions,
  OneDrive connection and Intelligence Center.
- **Forage / Deep Forage / Kali / Author / School**: their original
  app entries move out of their mistaken Study, System or Productivity
  assignments and into the matching native bays.
- **System**: legacy control center menu entries remain accessible,
  not deleted or used instead of native System.

These are **only category changes**. The actual binary, config, packages,
GNOME/KDE menu registrations, owner data and recordings remain intact.
Both Spider Studio `.desktop` entries are retained because they may
point to different entrypoints. The menus can be reviewed before
simplifying any redundant shortcuts.

**Read-only validation on the owner's existing checkout:**

```bash
git -C ~/spider-os-native-wave pull --ff-only

python3 -B ~/spider-os-native-wave/tools/ubuntu_studio_app_inventory.py \
  --compare ~/spider-studio-apps-before.json --strict

python3 -B ~/spider-os-native-wave/tools/ubuntu_studio_package_inventory.py \
  --snapshot ~/spider-studio-packages-before.json
```

The first command compares today's categorization to the original
174-entry snapshot. It reports category moves but returns failure if
an original menu entry disappears. The second checks the installed
`dpkg` package database and privately snapshots **all installed
packages**, including plugins and CLI tools with no launcher.
After a qualified release, compare the package inventory using
`--compare ~/spider-studio-packages-before.json --strict`.
Neither inventory requires sudo nor changes any package.

## October 15: native cockpit, playable instruments, Art Lab and no redundant control centers

The owner explicitly rejected the **three separate developer launchers**
created in a previous round because their purpose overlapped real native bays.
This upgrade preserves their engines but replaces their reason to exist as
standalone interfaces.

**One real native Home.** `the-web/shell/home_dashboard.py` now presents
the purpose, unfinished local mission count and installed program count for
each true bay. Selecting a card enters the existing native workspace, rather
than starting a separate application. The old anonymous launcher grid is gone.
Pinned favorites and installed Ubuntu Studio application menus are retained.

**Webbie, not "Webbie Intelligence Center".** The native Webbie bay gains
a `Webbie controls` tab with three existing owner-controlled services:
(1) cognition, local models, speaker-trust, voice test and privacy,
(2) local JARVIS evidence/search/site preview missions,
(3) supervised guided workflow. Existing computer-control permissions,
privacy controls and STOP rules are reused, never reset. No automatic
camera, listening device, web task or terminal execution is granted.

**Exact compatibility routing for yesterday's redundant shortcuts.**
The Web now redirects these internal menu requests to real bay surfaces
instead of launching additional competing windows:

| Existing menu entry | Native destination |
| --- | --- |
| `spider-os-universal.desktop` | The Web Home + Home's advanced analysis |
| `spider-os-workspace-max.desktop` | Home's advanced analysis; each bay has its own verified MAX module |
| `spider-webbie-intelligence.desktop` | Webbie > Webbie controls |

The user-owned `.desktop` registrations and possible icons in
`~/Desktop` remain untouched until inspected and explicitly approved
for retirement. In the regular KDE application menu, the originals are
still accessible as a fallback. The new audit tool can identify exactly
which icons exist without deleting any files:

```bash
python3 -B ~/spider-os-native-wave/tools/audit_legacy_shortcuts.py
```

**Real Studio sound creation:** `studio/instrument_engine.py` provides
offline deterministic WAV generation for keyboard tones, Karplus-Strong
plucked guitar/bass and four-voice 16-step drum patterns, with tempo
45–220 BPM and up to four bars. `studio/instrument_panel.py` adds a
playable native note keyboard, sequencer grid, optional local Qt audio
preview and explicit atomic WAV export. It is embedded in both standalone
*existing* Spider Studio and The Web's Studio bay. These are prototype
synthesized instruments, not accurate sampled guitars or a replacement
for Ardour, Guitarix, Hydrogen, JACK/MIDI or a commercial DAW. Audio
latency and playback still need real-hardware validation.

**Native Art Lab:** `the-web/shell/art_workbench.py` provides a
graphite/colored-pencil/marker/paintbrush/eraser canvas, color picker,
brush size, 12-step undo, local photo-to-ink outline extraction and
explicit atomic PNG export. An imported photo is protected from export
overwrite. This is a basic raster workbench, not yet blendable paint
simulation, native 3D editing or a Krita replacement.

**Data and system invariants:**

- All confirmed **174** owner-visible Ubuntu Studio menu entries remain
  registered; actual installed package/plugin inventory is separate.
- Existing Art, Author, Media/Nova, Studio, Kali, Study and Webbie user
  project files are not changed by GitHub code development.
- No `apt purge`, service restart, microphone/camera activation, reboot,
  root command or LUKS/GRUB/system upgrade accompanies this development.
- The real machine still has **31 unknown protected local modifications**.
  `release_batch.py check` must continue to block blindly replacing
  them; merging and rollback validation precede any owner installation.
- GitHub source/Qt smoke checks do not prove all features are usable on the
  owner PC. Check audio, GPU, Nova broadcast, Studio MIDI, Webbie identity
  gates and sound devices before treating as a releasable product.

## Owner-host live reconciliation result, October 15

The protected owner-PC audit has now been run **against the complete
monster development wave**, not the earlier 31-blocker release:

```text
Inspected: 260 release files | blocked: 33
custom_code_manual_merge: 33
No installed source modified; installation remains BLOCKED.
```

The **two additional blocker paths** relative to the previous 31 are
`the-web/shell/app_catalog.py` and
`the-web/shell/workspace_files.py`. This is expected: both were upgraded
to preserve and categorize all existing Ubuntu Studio programs.

All 33 files are **manual reconciliation required**; they are not
verified Git historical revisions. Do not rename, skip or bypass these
checks to force an install. The GitHub candidate source and installed
programs contain different changes. The current owner machine's
baseline contains 174 visible menu entries and 4,360 installed Debian
packages; the menu-preservation audit passed.

**Work in this dependency order:**

1. **Native desktop / live bay registration:** merge `the-web/shell/main.py`
   with local fixes; review `app_catalog.py`, `workspace_files.py`,
   `webbie_panel.py` and `webbie_cognitive_center.py`.
2. **Webbie resident runtime and trust:** preserve working wake/stop,
   allowed-speaker gating, model routing, owner approvals, voice audio,
   screenshot/operator actions. Merge the agent, brain, voice and panels.
3. **Actual creative bays:** Studio, Author, Forage, Deep Forage, Study,
   including local music catalog, spellings and book canon.
4. **Broadcast and security services:** preserve native BCN Nova running
   show clock, current Matilda voice, radio playlist/source and Podman
   Kali configuration. Never blindly restart or replace service units.
5. **Ancillary shell/OS and support files:** examine local touchups
   `quick_settings.py`, camera/face overlay, control sockets,
   grants, installers and all remaining files. Verify no unreviewed
   differences remain.

The source-only structural comparator
`tools/compare-native-2604.py` was upgraded to recognize both the
approved 26.04 reconciliation branch and this reviewed development
branch. It accepts `--focus desktop`, `--focus webbie`,
`--focus creative`, `--focus services` and `--all`.
It reads files under the installed native program tree but does not
execute, modify, or upload them. **No sudo required:**

```bash
git -C ~/spider-os-native-wave pull --ff-only
python3 -B ~/spider-os-native-wave/tools/compare-native-2604.py \
  --source ~/spider-os-native-wave \
  --installed-root /usr/local/lib/spider-os \
  --focus desktop
```

The output contains AST class/function **names and counts**, not
source bodies. For real manual merges, separately use the existing
`tools/jarvis_reconcile_preview.py --output` feature to produce
**private local-only diffs** (mode 0700/0600). Do not upload private
diffs without inspecting them for passwords, credentials or embedded
local host paths. Even a conflict-free three-way merge does not
authorize installation without owner-host tests and rollback proof.

## Private desktop integration staging after the owner review

The owner executed the structural comparator and confirmed that the
current **installed** The Web does **not** import
`immersive_bays`, `workspace_max_native`, `webbie_native_operations`,
`home_dashboard`, `art_workbench` or `instrument_panel`, while
all six exist in the incoming GitHub source. This is the key reason
why copying candidate-only modules cannot activate the upgrades.

A new local-only helper now prepares **paired copies of just the five
desktop integration files**, for safe Meld review:

```bash
git -C ~/spider-os-native-wave pull --ff-only

python3 -B ~/spider-os-native-wave/tools/stage_native_merge.py \
  --source ~/spider-os-native-wave \
  --installed-root /usr/local/lib/spider-os \
  --focus desktop \
  --output "$HOME/SpiderOS-Private-Desktop-Merge-20261015"
```

It verifies each file is in the guarded release catalog, rejects
symlinks, limits file sizes, and stages only private local copies under
the owner's home, with directories `0700` and files `0600`.
It creates `installed/`, `candidate/`, `diffs/`, a
sanitized `manifest.json` with symbol names and missing integration
imports, and a README cautioning against uploading private code.
The output directory **must not already exist**.

**This command does not merge or install anything.** Source files on
the actual PC are never modified; no authorization, service, model,
audio data, passwords, or personal project library is requested.
The staged code is private and must not be sent to public GitHub or
any chat without the owner's independent review/redaction.

Prioritize reconciling
`the-web/shell/main.py`, `app_catalog.py`,
`workspace_files.py`, `webbie_panel.py` and
`webbie_cognitive_center.py`, then re-run the structural comparison
before reviewing Webbie voice and safety, Studio, Author, Nova, Kali,
and the rest of the **33 protected customized files**.
The strict installer remains BLOCKED regardless of staged output.

## First-class native desktop

The user-facing navigation has **15 bays**, including The Web Home,
Webbie, Forage, Deep Forage, Studio, Author, Art Lab, Dev Bay, Study,
Media Center, Communications, Kali Bay, System, Productivity and Devices.

Legacy Recovery and Games keys remain in the internal registry to
preserve open tabs and saved user state, but are hidden from *primary*
bay navigation. Recovery has a real panel **inside System**; games
remain accessible as Media Center programs, without deleting saves.

## Working source delivered in this wave

| Bay / system | Implemented source behavior | What's not implied |
| --- | --- | --- |
| **Every first-class bay** | A native Mission Desk with private local projects, status transitions, linked folders and deliberate handoffs | Does not automatically read projects, move files or run other apps |
| **The Web** | Mission desks integrated into existing workspace tabs; full-size native panels primary; optional external app tools separated | Installed user's customized main.py still needs semantic reconciliation |
| **Webbie** | Native Research Mind with queued questions, references, uncertainty and follow-ups; owner-clicked handoff to existing chat; read-only agenda recall in brain.py | Does not certify source reliability, change current speaker gate, silently activate camera, or claim autonomous research is finished |
| **Studio** | Existing multitrack, mixing, QC/release native sources retained; shared production missions integrated | Actual PipeWire, plugin chain and exported audio must be tested on owner hardware |
| **Author** | Existing manuscript, canon, atlas and continuity native sources retained; project missions in its own bay | Existing private manuscripts remain on owner machine, never in Git |
| **Study** | Existing assignment, APA, milestone and revision native sources retained; projects stay in Study | No student login or submission without permission |
| **Kali Bay** | Existing isolated Kali/Purple tooling and evidence native sources retained; lab missions integrated | Never runs scans or installs containers automatically |
| **Media Center / BCN Nova** | Existing player bridge and radio tools retained; shared missions & schedules review | Actual Electron Media Center runtime packaging and real stream playback still require tests; old Player 7.5 must not replace the known-good Media Center |
| **Forage / Deep Forage** | Existing research engines retained; evidence missions and question handoffs | Citations and network results require independent verification |
| **Art Lab** | New built-in image preview and non-destructive PNG resize export | Not yet a full layer-based 3D/painting editor |
| **Dev Bay** | Native read-only Git tracked-change inspector | No automated commits, remote pushes or deployment |
| **Communications** | Native local text drafting, open/save with explicit confirmation | No unapproved email send |
| **Devices** | Native Linux device inventory for network, audio, cameras, USB, storage and input | No disk flashing, mounting or driver changes |
| **Productivity** | Real cross-bay active-mission overview plus personal mission desk | No calendar/cloud connection without opt-in |
| **System / Recovery** | Existing diagnostics, backups and repair UI retained, recovery surfaces inside System | No unattended bootloader, LUKS or kernel changes |

### Protected installation state

The previous live 26.04 preflight found **31 unknown locally customized
application files**. Those include The Web, Webbie's voice stack,
Studio, Author, Kali, Forage, Study and Nova. The guarded installer
must continue to reject blind replacement. **Do not use `apply`
on the owner PC yet.** Reconcile local changes with source, preserve
working versions, create and verify rollback backups, then smoke-test
the new native panels in a separate release qualification.

All user-created program data remain outside the public source repo.
Mission state is stored under
`~/.local/share/spider-os/native-bays/missions.json`;
research agenda under
`~/.local/share/spider-os/webbie/research-agenda.json`.
Both are private, bounded, atomic local files, and do not get committed.

### Testing and remaining release gates

- PyQt offscreen native desktop integration with real panel instantiation
- Mission store create/update/cross-bay/restore and symlink checks
- Webbie research question/evidence/follow-up persistence tests
- Device inspection and read-only Dev Bay Git source checks
- Existing native regressions and Webbie/Nova source checks
- Compare all customized installed modules against the candidate source
- Check real live KDE/voice/GPU, Studio audio, Media Center runtime,
  BCN Nova broadcasting, Kali Podman, camera and model routing
- Preserve the installed Ubuntu 26.04 LTS base, local data, bootloader,
  encryption, systemd user services and Spider OS rollback checkpoint

**No custom 26.04 ISO installation is approved.** Its Ubuntu Studio
26.04.1 Casper layout still differs from the previous ISO builder.

## Important unfinished user vision

The current batch is significant source development, not a declaration
that Webbie is fully autonomous or that every bay has become a finished
3D professional application. The 3D Broken World exploration, real
DAW engine integration, verified speaker identity under TV noise,
continuous interruption-safe live voice, full Media Center packaging,
hardware-specific Kali validation, and all-bay production acceptance
still require engineering and testing. Do not hide these gaps behind
extra desktop icons or green source-only checks.
