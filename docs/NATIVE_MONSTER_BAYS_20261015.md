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

## Desktop staged AST overlap review (after five-file private staging)

The first private owner-host staging completed successfully, with five
paired desktop files and no installed source changed:

- `main.py`: no local-only top-level definitions; **ten candidate-only
  native imports** not present in installed The Web.
- `app_catalog.py`: six candidate-only top-level functions supporting
  category placement, application descriptions and private assignments.
- `webbie_panel.py`: candidate-only `ConsoleWorker` class, whose
  grant/trust handling must be inspected before activation.
- `workspace_files.py` and `webbie_cognitive_center.py`: shared
  definitions exist but may have differing bodies or module settings.

**A zero local-only top-level definition count does NOT prove compatibility.**
A function with the same name can contain a locally essential audio, camera,
permission or state fix; a class can have differing methods without changing
the class's top-level name.

New tool `tools/review_staged_desktop_methods.py` makes a **read-only**
structural comparison of the staged private file pairs, after verifying
manifest identities, original source SHA256 hashes and stage permissions.
It prints only method/definition names, counts for shared changed methods,
argument/decorator changes, module settings/import changes and class bases.
It reads no projects, models, recordings or other files. It never imports
or executes owner Python code, writes a merge, or authorizes installation.

Run from the current separate GitHub checkout as the standard user:

```bash
git -C "$HOME/spider-os-native-wave" pull --ff-only
python3 -B "$HOME/spider-os-native-wave/tools/review_staged_desktop_methods.py" \
  --stage "$HOME/SpiderOS-Private-Desktop-Merge-20261015"
```

Only this **names-and-counts** terminal report should be shared for a
non-invasive merge plan. Staged `installed/`, `candidate/` and
`diffs/` contain actual local code, so keep them private. The strict
33-file reconciliation gate stays in place throughout.

## Verified five-file method conflict count and protected merge preview

The owner ran the private AST comparison of actual installed and GitHub
desktop code. It identifies **29 shared differing method/function bodies**,
**20 candidate-only definitions**, and **2 owner-only Webbie methods**:

| File | Shared differences | Candidate-only | Owner-only |
| --- | ---: | ---: | ---: |
| `the-web/shell/main.py` | 11 | 5 | 0 |
| `the-web/shell/app_catalog.py` | 2 | 6 | 0 |
| `the-web/shell/workspace_files.py` | 1 | 0 | 0 |
| `the-web/shell/webbie_panel.py` | 13 | 9 | 0 |
| `the-web/shell/webbie_cognitive_center.py` | 2 | 0 | **2** |

Crucially, the installed `WebbieCognitiveDialog.offer_workflow` and
`WebbieCognitiveDialog.open_workflows` are missing from the candidate.
The cognitive constructor also differs in both body and signature;
preserving these methods alone is not sufficient to retain safe behavior.
The installed Webbie panel has **one owner-only import** alongside 13
overlapping changes, including STOP, computer control, screen consent
and message sending.

A new owner-private `tools/draft_native_desktop_merge.py` creates a
**NON-INSTALLABLE source review overlay**, not a release. It preserves
owner-only class methods and imports inside a private copy of candidate
files, retains candidate-only methods, and explicitly reports unresolved
shared differences. It never edits the installed files or commits
any local owner code to public GitHub.

Run with the previously prepared private five-file stage:

```bash
git -C "$HOME/spider-os-native-wave" pull --ff-only

python3 -B "$HOME/spider-os-native-wave/tools/draft_native_desktop_merge.py" \
  --stage "$HOME/SpiderOS-Private-Desktop-Merge-20261015" \
  --output "$HOME/SpiderOS-Private-Desktop-Draft-20261015"
```

The output includes a private `draft/` tree and
`merge-review.json`. Draft modules must **NOT** be executed or
installed: the 29 overlapping methods still need semantic reconciliation.
A successful syntax parse alone is no evidence that grants, voice,
Nova radio, camera or local files remain safe. Existing application
packages and menus are untouched.

**Owner privacy rule:** do not upload `installed/`, `candidate/`,
`diffs/`, `draft/` or the full private report to public GitHub.
Only paste the terminal's method-name and unresolved-count summary
when planning the next step. A true deployable merge requires the
contents of the conflicting methods to be inspected *locally* and
validated with tests, preserving all prior host behavior. The guarded
33-file install gate stays BLOCKED.

## Actual owner-private preservation draft results and constructor review

Owner ran `tools/draft_native_desktop_merge.py` on the five staged
desktop files. The private `merge-review.json` records:

- **Three** unique installed imports retained: one each in
  `the-web/shell/main.py`, `webbie_panel.py`, and
  `webbie_cognitive_center.py`.
- Installed Webbie workflow methods
  `WebbieCognitiveDialog.offer_workflow` and
  `WebbieCognitiveDialog.open_workflows` retained.
- **29 shared method/function implementations unresolved** across
  `main.py` (11), `app_catalog.py` (2), `workspace_files.py` (1),
  `webbie_panel.py` (13) and `webbie_cognitive_center.py` (2).
- The private draft says `installed_modified=false`,
  `release_installable=false`, `safe_to_overwrite=false` and
  `install_allowed=false` for all five files. This is CORRECT.

Copying the two local-only Webbie workflow methods is insufficient:
their bodies might rely on instance fields removed from the candidate's
changed `__init__`, or call into candidate versions of changed
methods. We added a local-only AST review
`preservation_dependencies()` to
`tools/review_staged_desktop_methods.py`, which reports missing
owner-initialized constructor attributes and calls into changed shared
methods **by name only**. It does not execute owner code, open the
camera or change permission grants, but it may miss dynamic attributes.
A clean report is never approval to install.

```bash
git -C "$HOME/spider-os-native-wave" pull --ff-only
python3 -B "$HOME/spider-os-native-wave/tools/review_staged_desktop_methods.py" \
  --stage "$HOME/SpiderOS-Private-Desktop-Merge-20261015"
```

Before actual integration:
1. Use a local diff editor such as Meld to inspect the three private
   copies of Webbie's constructor/workflow methods. Do not publish
   private `installed/` or `draft/` files unreviewed.
2. Resolve `TheWeb.build_ui` and `TheWeb.open_workspace` against
   the working PC so the new bays are actually constructed without
   breaking navigation or restoring state.
3. Preserve permission-sensitive Webbie
   `stop_sensitive_actions`, `open_computer_dialog`,
   `send`, `set_face_sleeping` and resident voice gates.
4. Run all source/Qt tests and hardware smoke tests, then reconcile
   the remaining 28 owner-customized release files. **Do not call
   this source preview a complete merge or lift the installation gate.**

## Owner-host Webbie workflow dependency gap confirmed; candidate compatibility bridged

The owner ran the latest private class-method dependency checker:

```text
PRESERVE OWNER METHOD: WebbieCognitiveDialog.offer_workflow
  Candidate constructor missing owner-initialized fields:
    workflow_dialog, workspace_opener
  Constructor changed; verify callback/state compatibility
PRESERVE OWNER METHOD: WebbieCognitiveDialog.open_workflows
  Candidate constructor missing owner-initialized fields: none detected
  Constructor changed; verify callback/state compatibility
```

The candidate source is now adjusted **without changing owner-installed code**:

- `WebbieCognitiveDialog.__init__` supports optional
  `workspace_opener` as a distinct callback from
  `workspace_callback` (current workspace **getter**, not a navigation grant).
  It initializes `self.workflow_dialog=None` for backward compatibility,
  while preserving existing owner-click authorization rules.
- `WebbieNativeOperations` forwards the real workspace-opening callback and
  binds `cognitive.workflow_dialog` to its **one already-constructed supervised
  embedded workflow**, preventing duplicate control windows or sessions.
- `TheWeb.open_workspace` passes `self.open_workspace` through to the
  native Webbie controls. The existing `WebbiePanel.open_unified_workflow`
  path remains available for its own dialog flow.
- Offscreen GUI tests verify the distinct getter/opener roles and original
  callback is not invoked by constructing the dialog; Qt integration tests
  check the embedded widget alias and opener wiring.

**Important:** The actual contents of the owner's two locally preserved
`offer_workflow`/`open_workflows` methods have not been copied into public
GitHub, so their semantic compatibility with new callbacks is still
**unverified**. Nor are any of the 29 changed shared method bodies merged.
No claim of installability, live speaker verification, or working host
integration follows from this update. The 33-file release guard remains
BLOCKED.

To re-evaluate the changed candidate source against the same owner-installed
files, generate a new, different **private** stage directory:

```bash
git -C "$HOME/spider-os-native-wave" pull --ff-only
python3 -B "$HOME/spider-os-native-wave/tools/stage_native_merge.py" \
  --source "$HOME/spider-os-native-wave" \
  --installed-root /usr/local/lib/spider-os \
  --focus desktop \
  --output "$HOME/SpiderOS-Private-Desktop-Merge-Bridge-20261015"
python3 -B "$HOME/spider-os-native-wave/tools/review_staged_desktop_methods.py" \
  --stage "$HOME/SpiderOS-Private-Desktop-Merge-Bridge-20261015" \
  | sed -n '/^FILE: the-web\/shell\/webbie_cognitive_center.py/,$p'
```

The output should no longer list those two owner-initialized fields as
absent from candidate `__init__` **if** the current candidate is checked
out. It can still report constructor differences and must not be interpreted
as authorization to merge or install.

## Owner-first additive desktop integration preview (not installable)

The owner reran the desktop staging and verified the repaired candidate
`WebbieCognitiveDialog.__init__` now retains both previously missing
owner-initialized attributes, `workflow_dialog` and
`workspace_opener`. There are no constructor signature differences,
but `__init__` and `open_workflow` still differ semantically. The
candidate-only bay imports are **still missing from the installed shell**
because an installation has not occurred.

To make genuine progress beyond comparing names, the new
`tools/draft_owner_first_desktop.py` creates a **SECOND, owner-first**
review copy from the private staged pairs:

- Takes the owner's existing `installed/` files as the base.
- Preserves owner method/function bodies and existing module settings
  (AST fingerprints must match or staging fails).
- Adds candidate-only class/function definitions, unique methods,
  candidate-only imports and simple literal new settings where safe to
  append at source level.
- Keeps every shared changed method and setting explicitly
  **UNRESOLVED**. It never overrides the owner's working
  `TheWeb.open_workspace`, `TheWeb.build_ui`,
  `WebbiePanel.stop_sensitive_actions`, message/voice paths,
  or local-only Webbie workflow methods.
- Fails closed on parse errors, symlinks or altered private stage
  hashes; writes into a newly created private 0700 directory with
  0600 files. It neither executes modules nor modifies installed files.

Run as the normal desktop user after pulling the checked development
branch (use the **existing refreshed** Bridge stage):

```bash
git -C "$HOME/spider-os-native-wave" pull --ff-only
python3 -B "$HOME/spider-os-native-wave/tools/draft_owner_first_desktop.py" \
  --stage "$HOME/SpiderOS-Private-Desktop-Merge-Bridge-20261015" \
  --output "$HOME/SpiderOS-Private-Owner-First-20261015"
```

The tool prints **counts only** and stores `summary.json` plus
`review-only/` source files locally. Those source files and diffs
contain owner code; **keep private**. The additive preview is NOT an
executable or deployable release because the 29 shared differences
have not been semantically resolved, and candidate-only functions can
rely on different existing constructor/callback behavior. Do not
copy these preview files into system locations or publicly push them.

Before any deployment, compare both the candidate-first and owner-first
previews with the two originals in Meld, resolve shared method bodies,
test in a separate application sandbox, inventory installed packages,
and clear the guarded **33-file** owner-customization blocker. This
workflow specifically avoids replacing any original Ubuntu Studio menu
program and does not build new duplicate desktop launchers.

## Native merge workbench: review **actual method bodies** privately

The owner ran the revised owner-first desktop preview against the
private "Bridge" stage and verified that the tool staged 24 candidate-only
definitions/literals and 20 candidate imports, while preserving owner
methods in all five files. The report shows unresolved per-file counts
11 + 6 + 1 + 13 + 2 = **33 method/setting issues**, a distinct count
from the **33 protected local release files**. No files have been
installed or the guard lifted.

To move beyond abstract identifier reports, a new
`tools/private_method_workbench.py` prepares a static, offline-only
**15-conflict side-by-side HTML view** of the most consequential
overlapping definitions in the actual installed-vs-GitHub private stage:

- desktop startup, `build_ui`, `open_workspace`, original-app
  registry and `open_installed`
- `app_catalog.workspace_for` / `discover_apps`
- `workspace_files.workspace_folders`
- Webbie's `__init__`, computer authorization, STOP revocation,
  `send`, sleep/camera control, and cognitive workflow callbacks

All inputs are revalidated against the local stage manifest and source
SHA256 hashes. Original owner code is never executed. The output
`index.html` embeds fragments of real private source for local viewing.
The tool has no network functionality, uses a restrictive HTML content
security policy, and writes its only files into a **new owner-private**
0700 directory (files 0600), never into the installed program tree.

```bash
git -C "$HOME/spider-os-native-wave" pull --ff-only
python3 -B "$HOME/spider-os-native-wave/tools/private_method_workbench.py" \
  --stage "$HOME/SpiderOS-Private-Desktop-Merge-Bridge-20261015" \
  --output "$HOME/SpiderOS-Private-Method-Workbench-20261015"
xdg-open "$HOME/SpiderOS-Private-Method-Workbench-20261015/index.html"
```

Keep the HTML **on the owner's PC**. It contains private code; never
upload it, its screenshots, or its source bodies unreviewed. It is a
comparison viewer, **not** a merged runtime and cannot make a candidate
method safe by displaying it. The 33 customized files still require
semantic reconciliation and a validated rollback-aware release.

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
