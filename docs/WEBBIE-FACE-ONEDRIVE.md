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
- The Web's Webbie tab provides **Put Webbie to sleep** and **Wake face** actions.
  Quiet sleep leaves her portrait visible with closed eyes. Ordinary speech is ignored
  until an explicit wake command; background jobs and services keep running.
  The microphone/transcription listener remains active solely to hear the wake
  phrase, so this is NOT a hardware mute. Exact wake/sleep voice behavior requires
  the separate, reviewed agent upgrade; installing the visual add-on alone does
  not change the live agent.
- X11 only for now. Plasma Wayland input/stacking and fullscreen tracking need
  compositor-specific qualification. To check: `echo "$XDG_SESSION_TYPE"`.
- Auto-start via a normal per-user desktop entry in both Plasma X11 and The Web
  X11. Single-instance lock prevents duplicate overlays.
- If the overlay is closed, audio and Webbie still work.

Manual controls after installation:

```bash
python3 /usr/local/lib/spider-os/the-web/overlay/webbie_face.py sleep
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

## Selective installation on the already working desktop

The complete The Web desktop **does not need reinstalling** for this add-on.
From a checkout or extracted source archive of this PR:

```bash
bash the-web/package/install-webbie-extras.sh --check
sudo bash the-web/package/install-webbie-extras.sh
```

This installs the overlay launcher, two portrait files if missing, optional
OneDrive adapter and timer. It preserves your current Plasma/The Web shell,
customized Webbie panel, the installed AI agent and private files. GUI buttons
inside The Web's Webbie tab are additionally available when the combined
desktop batch is installed; the standalone menu launchers and Konsole actions
work without that batch. Signing out/in loads the auto-start overlay; it may
also be started manually in the existing **X11** session. No reboot required.

KDE application menu entries:
- **Webbie: Connect OneDrive**
- **Webbie: Sleep Quietly**
- **Webbie: Wake Face**

If `rclone` is missing, OneDrive connection cannot begin until you choose
to install it. The AI keeps running locally regardless. The cloud
workspace is a selected-file sync area, not a replacement for her models
or direct synchronization of private memory. Microsoft OAuth is never
requested during boot or installation.

## Acceptance checks on the installed PC

- Test Webbie overlay on both selected X11 sessions.
- Click several real buttons and window controls *through the visible face*.
- Play fullscreen video and check the face disappears and returns.
- Sleep Webbie; verify her face remains visible with closed eyes and no conversational voice responses. Explicitly wake her again.
- Ensure Webbie voice still replies even when rclone is absent/unconnected.
- Only after consent, complete OAuth and put a harmless sample note in the
  dedicated share. Check background transfer independently. No personal files
  are involved in source CI tests.
