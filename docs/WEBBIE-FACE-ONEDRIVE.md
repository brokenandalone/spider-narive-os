# Webbie floating face and optional OneDrive

**Release candidate.** Implemented as a separate, user-level enhancement to the
working KDE/The Web installation. Neither feature modifies Webbie's installed
agent, models, microphone, Ollama, boot process, Kali Bay or private manuscripts.
Owner-PC verification remains necessary.

## Floating face

- The small (196 px), partially transparent ethereal purple portrait is placed
  at the lower-left of the primary screen, just above the usual bottom panel.
- Uses Qt output-only window flags *and* an empty XFixes X11 **input region**.
  The cursor and all mouse clicks pass through it, including opaque portions.
  If mouse pass-through cannot be guaranteed, the overlay does **not** display.
- Watches the active X11 window and hides when it is in true fullscreen mode.
  This includes fullscreen videos. Unknown fullscreen status also hides it.
- Uses Webbie's existing speaking marker for an approximate mouth animation;
  sound/phoneme-accurate lip sync is not claimed.
- The Web's Webbie tab has **Sleep face tonight** and **Wake face** buttons.
  Sleeping hides the portrait until 8:00 AM local the next morning, or until
  manually woken. This does not shut down Webbie's resident voice service.
- X11 only for now. Plasma Wayland input/stacking and fullscreen tracking need
  compositor-specific qualification. To check: `echo "$XDG_SESSION_TYPE"`.
- Auto-start via a normal per-user desktop entry in both Plasma X11 and The Web
  X11. Single-instance lock prevents duplicate overlays.
- If the overlay is closed, audio and Webbie still work.

Manual controls after installation:

```bash
python3 /usr/local/lib/spider-os/the-web/overlay/webbie_face.py sleep-tonight
python3 /usr/local/lib/spider-os/the-web/overlay/webbie_face.py wake
python3 /usr/local/lib/spider-os/the-web/overlay/webbie_face.py status
```

## Optional OneDrive, no forced login or startup delay

Webbie's existing AI/service always starts **locally**. Signing in to Microsoft
is separate, user-initiated, and entirely optional. If never configured, her
voice, editor and offline models remain available.

1. Open the Webbie tab and select **Connect OneDrive** at any time, or run
   `python3 /usr/local/lib/spider-os/system/onedrive.py connect`.
2. A Konsole terminal opens the established `rclone config` interactive flow.
   Create a remote named **webbie_onedrive**, choose Microsoft OneDrive and
   sign in through the official browser/device authorization flow.
3. When the remote is configured, Webbie's OneDrive adapter activates the
   dedicated local folder
   `~/Documents/Spider OS/Webbie/OneDrive`.
4. A separate background user timer copies **only** files explicitly put in
   that folder to `webbie_onedrive:Spider OS/Webbie` every ~15 minutes.
   It never deletes or overwrites cloud files; use unique names for new
   versions of notes. Existing Webbie conversations and internal state are
   **not** uploaded automatically.
5. Pausing the OneDrive adapter stops further uploads without deleting data.
   Missing network, Microsoft authentication errors or absent rclone produce a
   skipped/failed timer run but never stall Webbie or the desktop.

The folder is a **selected shared-files workspace**, not yet a replacement for
Webbie's local brain, memory or models. Full cloud-memory read/query and
conflict-aware sync remain separate features requiring explicit scoping and
privacy review.

Privacy: rclone OAuth tokens remain in the user's own rclone configuration.
Protect that file and account. OneDrive itself is not end-to-end encrypted by
default. For sensitive personal material, use the existing Spider Vault
**encrypted** OneDrive snapshot process instead. Do not move medical records,
private transcripts or complete personal directories into Webbie's share by
default.

When the desktop installer is run, it installs the overlay application, the
opt-in adapter, a standard user-autostart entry and an independent timer.
If the user systemd manager is available, the timer is enabled. Otherwise
run **without sudo**:

```bash
systemctl --user daemon-reload
systemctl --user enable --now webbie-onedrive.timer
```

No Microsoft login is initiated at install time.

## Acceptance checks on the installed PC

- Test Webbie overlay on both selected X11 sessions.
- Click several real buttons and window controls *through the visible face*.
- Play fullscreen video and check the face disappears and returns.
- Sleep face tonight; verify it stays away, then wake it.
- Ensure Webbie voice still replies even when rclone is absent/unconnected.
- Only after consent, complete OAuth and put a harmless sample note in the
  dedicated share. Check background transfer independently. No personal files
  are involved in source CI tests.
