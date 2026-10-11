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
