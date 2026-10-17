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

## October 10 development follow-up

- [x] **Source-only** desktop-control Qt dialog integrated inside the resident
  Webbie panel, with a selected installed app, visible task description,
  five-minute/75-operation grant, independent risky-action confirmation,
  windows/focus/keys/type/click actions, and a user-visible STOP WEBBIE control.
  It starts denied; no request alone can activate the permission grant.
- [x] **Source-only** single authorized selected-window JPEG snapshot in memory
  and optional loopback Ollama screenshot description (no screenshot files);
  separate on-screen consent for each inspection.
- [x] **Source-only** stop propagation from agent to desktop-panel grant via a
  private one-way marker, with symlink checks and no authorization channel.
- [x] **Source-only** interruptible edge-tts/mpv/espeak subprocess wrapper,
  background reply thread, and single-microphone Whisper stop-only barge-in
  during speech, recognizing exact Webbie/Webby stop commands. This is not
  proof of reliable speaker/echo separation on the installed webcam microphone.
- [x] **Source-only** strict voice "open Audacity" routing through a local
  Unix socket exposed solely while the owner-selected desktop task is active.
  The spoken request must match the exact approved installed-app desktop ID.
  No voice command can create a grant, switch apps or submit arbitrary GUI
  actions. The UI uses the user's installed XDG launcher rather than model
  string execution.
- [x] Reversible release manifest updated with matched new module sources.
  Unknown owner-customized live files must BLOCK installation until manually
  reconciled.

**Still absent:** reliable autonomous multi-step GUI planner and verifier,
selected-window confinement of pointer/keyboard actions, owner/Shayna
speaker-grade authorization and hardware-tested TTS barge-in. The local GUI
still requires direct user operation of its controls after permission, except
for explicit voice app-open requests. Do not claim full remote/agentic control.

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

## October 10: Supervised Autopilot and PC comparison requirement

- [x] Built a source-only **Supervised Autopilot** for a single explicitly
  owner-selected X11 window and a user-approved task. It can take a short
  sequence of fresh screenshots locally, propose an ordinary navigation step,
  execute a navigation key when confidence is at least 0.90, and rescan
  afterward. Mouse clicks still require user review. No generic form submit,
  automatic typing, file deletion, software installation, purchases, outgoing
  messages, terminal commands or privilege changes.
- [x] Autopilot refuses high-impact tasks, times out after 120 seconds or six
  actions, pauses on repeated actions or uncertainty, and fails closed when the
  selected window or grant changes. The GUI has Start/Pause/STOP controls.
- [x] Added read-only comparison tooling at
  `webbie/tools/installed_reconcile_audit.py`. It examines relevant PC
  source modules and prints source hashes plus feature-marker differences.
  **It has NOT been run on the owner's currently installed desktop in this
  GitHub-only development session.** Do not claim a live PC comparison.
- [ ] **Critical prerequisite for installation:** reconcile the current PC
  code against this precise PR head rather than the historical frozen commit.
  The October 9 PC audit reported the installed Webbie agent had ~2,300 lines
  versus ~965 in the older GitHub release, and brain.py ~850 versus ~147.
  PC additions include conversation/history/long-term memory, Forage/Firefox
  research and navigation, voice echo/interruption behavior and a 45-second
  conversation window. The user subsequently confirmed camera and live preview
  with local vision working, alongside updated Ollama models, so preserve all
  of those changes. Historical October 9 hashes are not proof the PC is still
  byte-identical today.
- [ ] Do not run the release installer or replace live voice/camera modules
  until the on-PC read-only report is reviewed and a detached merged candidate
  passes full integration and rollback checks. Preserve user data and current
  TTS, face, author library, Studio, Media Center and system services.
- [ ] Autopilot is not a security sandbox. No end-to-end speaker authentication
  or arbitrary multi-application operation has been tested on the PC.

Read-only terminal check, from an exact checkout of this PR branch, as the
normal user (no sudo):

```bash
python3 webbie/tools/installed_reconcile_audit.py --checkout "$PWD"
```

The report intentionally refuses to authorize installation even if hashes
match. A reconciliation HOLD is expected for customized on-PC modules.
