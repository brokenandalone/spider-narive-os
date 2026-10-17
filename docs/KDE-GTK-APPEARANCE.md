# KDE and GTK appearance checks

Source implementation; actual Dell appearance acceptance remains pending.

Quick Settings shows **App color preference** alongside the existing KDE,
GTK 3 and GTK 4 configuration entries. Refresh asks the session desktop portal
for its public color-scheme preference on the existing background worker.
Each command has a two-second timeout; the legacy fallback can add another
two seconds. Closing waits for the bounded worker to finish.

- **Dark preferred / Light preferred:** the desktop preference available to
  apps using the portal. Apps with independent settings can still differ.
- **No preference:** the desktop leaves the choice to the app.
- **Unavailable:** the portal, session bus or optional `gdbus` client did not
  answer. This is not interpreted as light mode.
- **Unknown:** an unexpected reply was rejected, without displaying its text.

**Preview KDE / GTK coordination** compares the last refreshed app preference
with the selected The Web appearance. The preview performs no new bus call on
the GUI thread. Refresh again after changing settings in KDE or another app.

Changing The Web's appearance still affects The Web alone. This diagnostic
does not apply a global theme, modify GTK files, restart services or access
camera/screen content. `gdbus` is optional; its absence leaves other settings
usable. The portal may be normally activated by the session bus when queried.

Implementation follows the [XDG Settings portal specification](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Settings.html):
ReadOne (version 2), Read fallback (nested variant), and unsigned color-scheme
values 0/1/2. Unknown numeric values mean no preference.

## Acceptance during the combined installation

1. Open Quick Settings and Refresh in the real The Web session.
2. Check the reported preference against KDE Settings and a portal-aware GTK
   app, including its own light/dark override if present.
3. Open the coordination preview and confirm it explains mismatched choices.
4. Confirm a missing portal produces a readable unavailable status while the
   desktop remains responsive.
5. Keep global theme switching and rollback unchecked until separately built
   and verified on the host.
