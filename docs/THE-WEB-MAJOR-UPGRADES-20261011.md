# Spider OS · The Web major desktop upgrade (2026-10-11)

## Baseline and scope

This work continues pull request #52 and remains based on
`release/combined-20261010-audit-gate`. Do not install the old repository
`main` version of `the-web/shell/main.py` over the current installed shell.

The changes are confined to The Web's source and regression tests. They do not
overwrite existing KDE preferences, wallpapers, document files, Spider Studio
projects, Webbie voice authorization, or the system login manager.

## New capabilities

1. **Quick Launch:** Ctrl+K, the header's **Quick Launch**, or taskbar **Find**
   opens a live search across existing Spider OS workspaces, installed XDG
   applications, and a fixed set of desktop actions. Enter opens a match;
   Up/Down navigate; Escape closes the launcher.
2. **Search ranking:** whole-name and word-prefix matches rank ahead of
   descriptive matches. Pin and recent history raise useful results. Search
   queries cannot invoke arbitrary shell commands.
3. **Pinned workspaces:** use **Pin selected** in Quick Launch. The Web home
   shows up to eight pinned workspace buttons. While The Web has keyboard
   focus, Ctrl+Alt+1 through Ctrl+Alt+8 open the corresponding pinned
   workspace. Pinned apps are searchable in Quick Launch.
4. **Recent work:** the home screen shows recently opened workspaces and
   currently installed applications. Missing applications are not launched.
5. **Responsive application scanning:** XDG desktop-file discovery runs in a
   QThread, so the desktop remains interactive while discovering applications.
   Refresh is explicit through Start, Quick Launch, or the existing workspace
   panels. There is only one scan in progress at a time.
6. **Responsive taskbar:** X11 window listing runs in a background QThread.
   Buttons remain clickable while a refresh runs; the display uses available
   width and puts excess applications into the existing Windows overflow menu.
   All window close operations still use ordinary close requests, allowing
   applications to prompt about unsaved work.
7. **Safe session restoration:** open tabs and active workspace are stored in a
   bounded, versioned, private, atomic file. Invalid or corrupt state falls
   back to The Web home. Tab order is retained. Closing during an ongoing
   refresh is deferred instead of destroying a running Qt worker.
8. **Readable desktop controls:** high-contrast menus, larger text options,
   screen-safe Start-menu placement, keyboard activation from search, and
   saved appearance preferences from the earlier part of PR #52.
9. **Persistence:** navigation preferences are in
   `~/.config/spider-os/navigation.json`; tabs remain in
   the existing `desktop.json`, and menu readability in
   `readability.json`. Writers use private `0600` temporary files,
   atomic replacement, bounded values and symlink refusal.

## Code touched

- `the-web/shell/main.py`: asynchronous app/task lists, home screen,
  launcher navigation, session management.
- `the-web/shell/command_palette.py`: non-modal Qt keyboard launcher.
- `the-web/shell/navigation_core.py`: deterministic search ranking.
- `the-web/shell/navigation_state.py`: pinned/recent persistence.
- `the-web/shell/desktop_state.py`: safe desktop state serialization.
- `the-web/shell/readability.py` and `quick_settings.py`: legible menus
  and accessibility preferences.
- `tests/test_web_major_navigation.py` and `tests/test_web_readability.py`:
  no-display regression tests.
- `tests/check-the-web.py`: offscreen Qt integration covering shell
  tabs, window controls, launcher, wallpapers and editor state.

## Source and integration verification

Run in a checkout of this branch:

```bash
python3 -m unittest discover -s tests -p 'test_web_major_navigation.py' -v
python3 -m unittest discover -s tests -p 'test_web_readability.py' -v
python3 -m py_compile the-web/shell/main.py the-web/shell/command_palette.py the-web/shell/navigation_core.py the-web/shell/navigation_state.py the-web/shell/desktop_state.py
QT_QPA_PLATFORM=offscreen dbus-run-session -- python3 -u tests/check-the-web.py .
```

Check GitHub **Spider OS source checks** for the full regression run before
merging or deploying.

## Required live-desktop checks

1. Confirm The Web, Studio, Author, Study, Webbie, Forage, Deep Forage and
   Kali Bay still open as native tabs. Author/Study edits should survive a
   normal close and reopen.
2. Use Ctrl+K to search an app. Verify it opens through the existing XDG
   launcher, not a raw command interpreter.
3. Pin a workspace, try Ctrl+Alt+1, unpin it, and confirm the home screen
   updates. Open a program and check Recent on the home screen.
4. Open five ordinary windows. Verify taskbar/overflow entries can activate,
   minimize, maximize and request a normal close without freezing The Web.
5. Refresh installed applications, switch workspaces during the scan, and
   verify search results appear afterward.
6. Switch dark/light menus and the 16/19/22 px text options. Test keyboard
   selection and popup placement at reduced display scaling.
7. Restart only after local backups and verify the saved tab order, active
   workspace, pinned items, appearance and wallpaper.

## Installation caution

This is GitHub source, not an automatic PC-side update. The Spider OS computer
already has separately installed October 10 fixes and possibly additional
local changes. Compare the checkout to its installed files before replacing
anything. Keep backups and a known working desktop/login session. The SDDM
keyboard/mouse login fault is **out of scope** for this change.

Webbie's separate permission-gated computer operator remains untouched.
Quick Launch is user-driven and does not independently grant Webbie control
over arbitrary windows, apps or the terminal.

## Further desktop upgrade: workspace control and Quick Launch

The second October 11 round extends the same GitHub PR and keeps the current
combined-release baseline.

- **Reorder tabs:** drag workspace tabs to rearrange them. The Web home is
  automatically restored to position zero. Saved session order follows the
  actual visible tabs and is restored at the next normal session launch.
- **Cycle tabs:** Ctrl+PageDown and Ctrl+PageUp switch to the next/previous
  workspace tab. Ctrl+Alt+Home returns to The Web home without closing work.
- **Tab context menus:** right-click a tab for Open, Pin/Unpin, Close, Close
  Other Workspace Tabs, and Home. Closing tabs still invokes each native
  workspace's existing save and pending-worker checks. A rejected close stops
  the Close Other operation.
- **Quick Launch window search:** while the X11 desktop session is active,
  recently enumerated open-window titles appear as search results. A selected
  window is activated only if its X11 ID matches the shell's fresh, bounded
  taskbar snapshot. Search text never executes commands.
- **Clear recent history:** Quick Launch has a confirmation-protected
  Clear Recent action that clears recent launcher history without touching
  favorites, files, windows, or open tabs.
- **Webbie workspace context:** the assistant's existing advisory workspace
  context now lists the current workspace and other open workspace **labels**.
  The shell does not automatically add window titles, URLs, document contents,
  clipboard text, or arbitrary X11 observations. Webbie's computer-operator
  authorization flow remains unchanged.

### Additional tests

```bash
python3 -m unittest discover -s tests -p 'test_web_navigation_round2.py' -v
QT_QPA_PLATFORM=offscreen dbus-run-session -- python3 -u tests/check-the-web.py .
```

The offscreen test now verifies saved tab ordering, the permanent home tab,
keyboard cycling, scoped Webbie labels, verified X11 activation, and clearing
recent history. These automated checks are not a substitute for live X11
interaction testing (including input focus and multi-monitor popup placement).

## Round 4: desktop recovery and session reliability

The Web now includes a **Recovery** control in the header, Start menu, and
Ctrl+K Quick Launch. Use Ctrl+Alt+R while The Web has keyboard focus.

- **Native workspace diagnostics:** inspect source presence and currently
  loaded workspaces without running missing modules or reading private project
  files. A failed workspace is marked "needs attention" and offers Retry.
- **Error fallback:** if a native module raises an exception during loading,
  a usable workspace shell remains open with a Retry option rather than an
  unexplained empty screen. Module exception types are not forwarded to the
  AI assistant or broadcast to other applications.
- **Explicit layout checkpoint:** Recovery can save and restore workspace
  *tab order and the active tab*. Existing open editors stay open. These
  checkpoints contain workspace IDs only and do not back up documents.
- **Private checkpoint file:** `~/.config/spider-os/desktop-checkpoint.json`
  uses bounded JSON, restrictive file permissions, atomic replacement, and
  symlink refusal.
- **Safe-start:** launching `python3 the-web/shell/main.py --safe-workspaces`
  skips automatic workspace restoration. Safe-start preserves the previous
  desktop tab state rather than replacing it with a one-tab home session.
  Restoring a checkpoint explicitly exits safe-start for that session.
- **Safety:** The Recovery Center does not edit KDE/SDDM, auto-install
  packages, repair code or replace previously saved manuscripts. Workspace
  retry is requested by the user, not Webbie autonomous control.

### New tests
```bash
python3 -m unittest discover -s tests -p 'test_web_recovery.py' -v
QT_QPA_PLATFORM=offscreen dbus-run-session -- python3 -u tests/check-the-web.py .
```
The Qt smoke test covers the Recovery dialog, checkpoint round trip, safe
starting with the home tab and preservation of the existing desktop state.
Actual PC startup and recovery need a real Spider OS X11 session test before
merging or installing. Use the preexisting full-system daily installation
and reconciliation process, not a direct `main.py` overwrite.

## Round 5: staged desktop startup and first-paint responsiveness

When launched as a real X11 desktop session (`--desktop-session`),
The Web now reads the previous tab layout but defers reopening heavy native
workspaces until the Qt event loop runs. It shows Home first, then loads each
saved workspace in a separate UI event-loop turn and shows a progress label.
This avoids constructing every restored workspace before first paint and
reduces the length of an entirely unresponsive startup. Native workspace
construction still occurs on the GUI thread, because Qt widgets must not
be built on background workers.

- **Stable restoration plan:** invalid/duplicate tab identifiers are filtered
  through the existing bounded session reader. The original user-set tab
  order is restored when the staged operation completes.
- **User navigation preserved:** if the owner chooses a tab during startup,
  finishing restoration does not automatically steal focus back to the
  previously saved active tab.
- **Recovery timings:** the Recovery Center displays the slowest three
  observed workspace construction times for this shell session. These
  metrics contain workspace IDs and elapsed seconds only.
- **Explicit safe-start resume:** Recovery offers a confirmation-protected
  "Resume last saved session" action only after starting with
  `--safe-workspaces`. Safe-start itself still does not reopen or overwrite
  the saved tabs.
- **Normal test window unchanged:** a standalone non-desktop `TheWeb()`
  continues using immediate restoration for development and the
  existing offscreen regression tests.
- **Checkpoints remain user-driven:** manual restore cancels the pending
  staged restoration plan before applying a checkpoint.

### Verification
```bash
python3 -m unittest discover -s tests -p 'test_web_restore_plan.py' -v
QT_QPA_PLATFORM=offscreen dbus-run-session -- python3 -u tests/check-the-web.py .
```

The integration test exercises deferred restoration with `desktop_mode=True`,
checks the saved active tab and measured construction times, and resumes a
minimal safe-start shell on explicit user request.

**Limitations:** this change does not make heavy Qt workspace constructors
non-blocking. Each individual workspace can still occupy the GUI thread
during its own initialization. The first launch and subsequent event-loop
scheduling require live visual testing on the actual Spider OS PC. No code
in this branch is automatically installed on the device.

## Round 6: interruptible restoration and private diagnostics

This extends the *same* October 11 source branch, without changing the
installed PC, user documents, X11 security policy, or Webbie task grants.

### Controllable restoration queue

The **Recovery** panel can now pause/resume the staged restore process,
prioritize a queued workspace for next launch, skip a queued workspace for
this startup, or stop restoring the remaining queue.

- A manual launch of a still-queued workspace is acknowledged and not
  launched a second time by the queue.
- Pausing does not discard pending tabs. Resuming schedules the next
  workspace on the Qt event loop.
- Skipping is a *startup-only* decision. Skipped workspaces and their saved
  identities remain in the original stored session file.
- Stopping cancels the pending operations, not the already opened editors.
  The previous saved tab arrangement is preserved.
- If even one workspace was intentionally skipped, The Web will not silently
  replace the previous startup layout with the partial session when closing.
- To intentionally save the current arrangement, choose **Save current
  layout as default** in Recovery and approve the confirmation. This explicit
  control is disabled during active restoration.
- Original tab ordering is independent of temporarily prioritized loading.
  The Web preserves the visible navigation choice made during recovery.

This does not kill a *currently executing* Qt workspace constructor. Each
individual native workspace loader still runs on the GUI thread and must
finish before the queued control action can be processed.

### Owner-approved safe desktop report

Recovery now offers **Copy safe diagnostic report**. Only a direct button
click copies the report to the local clipboard. Nothing is uploaded or sent
to Webbie.

The report is limited to known workspace IDs, current/open workspace names,
module health states, bounded load timings, restoration status, safe-start
flag and counts of installed apps and open X11 windows. It does not read
or include the titles of windows, browser URLs, personal filenames, paths,
document text, clipboard contents, passwords, microphone, webcam or logs.

### Verification

```bash
python3 -m unittest discover -s tests -p 'test_web_restore_plan.py' -v
python3 -m unittest discover -s tests -p 'test_web_desktop_diagnostics.py' -v
QT_QPA_PLATFORM=offscreen dbus-run-session -- python3 -u tests/check-the-web.py .
```

Qt smoke tests now cover pausing, priority, skip protection, stopping,
explicitly adopting the partial layout, and copying the safe report. Verify
actual keyboard focus, responsive status updates and visually readable
Recovery controls on the Spider OS computer before installing.

Known limitation: restoring a large native workspace can still block the
UI while *that particular workspace* is initialized. The per-workspace queue
gives control between loads, not during a single synchronous constructor.

## Round 7: local user-service health and owner-reviewed Webbie advice

Recovery now includes a separate **System Services** section. It checks four
allowlisted user services: `webbie.service`, `spider-ai-dj.service`,
`webbie-proactive.service`, and `webbie-research.service`.

- A Qt worker reads only the `LoadState`, `ActiveState`, and `SubState`
  fields via `systemctl --user show`. Each probe has a bounded timeout;
  no shell string interpolation or privileged commands are used.
- The Recovery interface stays responsive while checking systemd. Statuses
  are normalized to `running`, `starting`, `stopped`, `failed`,
  `masked`, `not-installed` or `unavailable`. Raw systemd output and
  journal logs are neither displayed nor sent to Webbie.
- Service checks refresh on demand and at most once per 60 seconds while
  Recovery is visible. Missing/unavailable units are informational only.
  A stopped optional unit does not automatically mean the OS is broken.
- A separate **Ask Webbie about status** button prepares a *draft* in the
  existing Webbie input box containing only allowlisted unit names and
  normalized states. The user reviews and sends it. If Webbie is busy or
  already has an unsent draft, the button leaves it untouched.
- No command is run on Webbie's behalf, no auto-repair/restart/enable occurs,
  and existing voice authentication and desktop-control grants are unchanged.
- The host shell guards against destroying the Recovery widget while the
  systemd probe worker is running.

### Round 7 tests

```bash
python3 -m unittest discover -s tests -p 'test_web_service_health.py' -v
QT_QPA_PLATFORM=offscreen dbus-run-session -- python3 -u tests/check-the-web.py .
```

Tests cover the service allowlist, read-only argument vector, timeouts,
missing/masked/failed states, rejected untrusted state text, the desktop UI
worker result rendering, and no-send Webbie draft preparation. Live PC service
status has **not** been queried or changed from ChatGPT.
