# The Web menu readability upgrade · 2026-10-11

## Baseline
Based on `release/combined-20261010-audit-gate`, not the older `main`
or the former desktop branch. This is a focused source upgrade, not a live
Spider OS installation or a KDE login-screen repair.

## Improvements
- Solid contrasting colors for Qt context menus, nested menus, combo-box
  drop-down lists, app lists, search results and tooltips in dark and light mode.
- Independent shell menu text sizes: Comfortable 16 px, Large 19 px (default),
  Extra large 22 px. Change in **Taskbar → Quick → Menu text readability**.
- Persist choice privately in `~/.config/spider-os/readability.json`.
- Start-menu search opens the selected first result when Enter is pressed.
  No-result searches show a clear message.
- Start menu stays inside the screen's available geometry where possible.
- Existing purple wallpaper assets, native workspaces, Webbie panel, taskbar,
  44px shell button minimums, desktop state and KDE appearance remain intact.

## Source changes
- `the-web/shell/readability.py` (new, pure Python configuration and stylesheet)
- `the-web/shell/main.py` (The Web integration, Start menu behavior)
- `the-web/shell/quick_settings.py` (menu text size control)
- `tests/test_web_readability.py` (preferences, contrast, validation and symlink safety)

## Validation
With Python available in a clean checkout:

```bash
python3 -m unittest discover -s tests -p 'test_web_readability.py' -v
python3 -m py_compile the-web/shell/readability.py the-web/shell/main.py the-web/shell/quick_settings.py
```

On a Spider OS X11 desktop, verify visually:
1. Start menu: searchable text, hover states, Enter launches first match.
2. Workspace selector and wallpaper selector: readable popup choices in both themes.
3. Quick Settings → Menu text readability: try all 3 values, close/reopen, sign out/in.
4. Window-taskbar right-click menu, Windows overflow menu and background-app menu.
5. Native Studio, Author, Study, Kali Bay and Webbie tabs still open and close.
6. External KDE applications, wallpapers, voice services and login screen unchanged.

## Safe deployment
Do **not** replace the installed `main.py` by copying an unrelated old
repository branch. Compare with the PC's installed files, back up its
`/usr/local/lib/spider-os/the-web/shell` tree, and run syntax tests before
staged installation. Log out and back in only after backups and smoke tests.
This branch does not include a live installer or claim an on-PC deployment.

## Scope limit
This update improves The Web's own Qt menus, not the SDDM greeter or KDE
login keyboard/mouse handling. Those are separate recovery tasks.
