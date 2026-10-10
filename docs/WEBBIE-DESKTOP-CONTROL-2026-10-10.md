# Webbie: installed camera acceptance, visible sleep, stop and full desktop operator

Owner report, October 10, 2026:

- On the actual Spider OS PC, Webbie's upgraded camera works. **Accepted on device.**
  Do not relabel camera as uninstalled or replace its successful settings.
- The portrait displays Zs at bedtime but her original pupils remain visible.
- Saying "Webby stop" often fails to interrupt her.
- Requested end state is controlling any **installed desktop application**, not
  just Spider OS bays, when explicitly asked by an authorized user.

## Added source in this branch

1. The existing Webbie portrait overlay now **masks the still-image open eyes**
   and paints eyelids/creases in quiet sleep mode. Previously only two thin
   arcs were painted; the static open eyes stayed visible. Separate offscreen
   tests inspect the eye-area pixel colors and ensure other facial areas are
   not masked. The original PNGs and click-through X11 input transparency remain
   unchanged. On-device face appearance/placement still needs owner review.
2. A local X11 **desktop operator foundation** reuses The Web's established XDG
   installed-application catalog. It can enumerate launchable desktop entries,
   disambiguate exact app names, request launch through gio, list existing windows,
   focus windows, click coordinates, type restricted one-line text, press vetted
   shortcuts, and request a window close. It has an emergency stop flag. Desktop
   actions use fixed subprocess argument arrays, never shell=True, arbitrary
   commands, Python eval, unvalidated terminal commands or privileged execution.
3. Permissions default to **DENIED**. A future trusted GUI must provide the
   authorization callback for a user-selected task and confirm each risky change.
   An AI model, recognized text, window title, camera image, screen contents or
   named speaker are not authorizers. Window titles can contain private content,
   so reading the list also requires explicit local permission. A session may
   be stopped regardless of authorization; resuming requires fresh approval.
4. The Webby/Webbie direct-stop matcher now recognizes complete phrases such as
   "Webby stop", "Hey Webbie stop talking" and "Webbie cancel that", while
   ignoring quoted material and longer sentences. This is a **classifier only**,
   not an installed voice hotword/interrupt implementation.

## Remaining integration work before Webbie can operate apps on demand

- Build the owner-visible control permission surface, foreground task indicator,
  action preview and manual emergency-stop control. Add an auditable timeout and
  separate confirmations for deleting, publishing, transferring money, installing
  software, sending communications, saving over originals and privileged changes.
- Attach the desktop operator to the **reconciled newer installed** agent only
  after the owner-approved microphone/voice authorization gate. Preserve the
  working camera, learned context, Qwen preferences, installed speech repairs,
  the Author library and the newer desktop. A wake word or facial recognition
  result by itself is not reliable authorization.
- Add active-window screenshot observation with a visible sharing permission,
  protected-window redaction, limited memory retention and on-screen verification.
  Without the visual feedback loop, coordinates should come only from the user's
  own explicit direction; the assistant cannot reliably work its way through a
  complex GUI without seeing it.
- Implement true **barge-in**: while talking, a dedicated interrupt recognizer
  must still be able to hear an authenticated "Webby stop", cancel audio output,
  stop pending desktop actions, and reset the conversation state. The previous
  Whisper listener skips *all* listening while the speaking marker exists;
  string matching in the same blocked listener will not solve this.
  Prevent Webbie's own audio or media playback from becoming commands.
- Test the installation on the owner's X11 display in Audacity, a browser, a
  document editor and the native Spider bays; validate stop while speaking,
  task cancellation, screen access controls, trusted-user separation and denial
  of unrequested actions.

## Delivery policy

**Source-only development PR.** No connected GitHub operation installs code,
captures camera/audio, reads the PC's windows, grants application control or
starts an automation on the owner's computer. Stacked on the Webbie full-screen
portrait branch; reconcile with PR #30 memory repair and newer installed
voice/visual files before a single backup-first, reversible install.
