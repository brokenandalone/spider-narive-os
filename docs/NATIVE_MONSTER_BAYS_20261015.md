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
