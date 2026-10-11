# Webbie proactive reliability and local reminders · 2026-10-11

**GitHub source implementation only. NOT installed or approved for the
customized Spider OS PC.** This work builds on PR #54, which in turn is
stacked on the guarded release PR #49. Keep all branches in their original
order; do not cherry-pick the shorter GitHub agent over the customized PC.

## Why the old behavior was unreliable

Before this change, the GitHub resident loop only greeted on login and
issued a generic "do you need anything?" every 45 minutes. It skipped the
interaction when the desktop was idle/asleep; it did not inspect local
services, store actionable check results, remember pending alerts, or explain
what was checked. On PCs with more than one login session, it also stopped
examining sessions after finding the first matching user, even if another
same-user session was active.

## What is implemented in source

### Real local checks

- The running Webbie agent checks: **HOME filesystem free space**,
  **Ollama loopback health** (fixed local endpoint only), and the last
  reported **microphone-listener status**. Optional BCN AI DJ **systemd
  user-service** monitoring is available, initially OFF.
- Source defaults: on at startup, check every **45 minutes** (configurable
  5 to 1440), initial check about 8 seconds after startup, warn once for
  each new failure, suppress repeated identical warnings for **180 minutes**,
  notify on genuine recovery, and suppress notification during **22:00–08:00**
  local quiet hours or while Webbie is asleep / the session inactive.
- Checks continue to update their private status during sleep. Alerts that
  couldn't be delivered are retained. Short summaries are visible through
  read-only "Webbie, what have you checked?" and in The Web's Webbie panel.
  Proactive status data never contains screenshots, audio, secrets, calendar
  entries, or document content.
- The Web now includes **Show Webbie system checks** and **Run system checks
  now**. The latter sets a private owner-local request marker and asks the
  resident worker to perform read-only probes on its next tick, with a
  30-second throttle. It does not force-launch a browser, model or service.
- The source state writer is now atomic with `0600` permissions, and the
  login/session checker examines all same-user sessions with timeouts.

### On-device local reminders

- The Web's **My local reminders** dialog provides explicit Add/Remove.
  Reminder names and dates are never extracted from overheard speech, camera
  descriptions, model output or web pages.
- Supported schedules: **once**, **every day**, **every week**. Dates are
  entered in the host's local wall-clock time. Daily/weekly reminders recur
  on their intended local day/time across local clock changes; weekly uses
  the weekday of the selected start date.
- Limit: 50 reminders. At most 5 notifications on one polling tick.
  Delivery only when the owner desktop is active, Webbie is awake, and
  outside the configured quiet interval. A failed notification is retried.
  Delivery receipts survive service restarts in a separate private file,
  preventing repeat notifications for the same occurrence. One-off
  reminders over 24 hours late are deliberately not delivered.
- This is a local reminder feature, NOT verified school OneDrive sync,
  live Google/Microsoft calendar sync, accurate AA/NA meeting discovery or
  recognition of Cory/Shayna's voice. Those remain separate integrations.

### Configuration

`webbie/config/default.json` has a `proactive` object:

```json
{
  "enabled": true,
  "check_in_minutes": 45,
  "alert_cooldown_minutes": 180,
  "quiet_start": "22:00",
  "quiet_end": "08:00",
  "disk_warning_free_gib": 5,
  "watch_ai_dj": false,
  "notify_recovery": true
}
```

Service-status checks intentionally do **not** infer that BCN Radio is on-air;
that requires independent verified station telemetry. Microphone-listener
status is not a successful microphone hardware test. No automatic disk
cleanup or system service restart occurs after a warning.

## Review and test (read-only, no hardware required)

```bash
python3 -m unittest discover -s tests -p test_webbie_proactive_checks.py -v
python3 -m unittest discover -s tests -p test_webbie_local_reminders.py -v
python3 -m unittest discover -s tests -p test_webbie_voice_queue.py -v
python3 -m unittest discover -s tests -p test_webbie_interruptible_speech.py -v
```

In the same guarded release candidate, source CI should also validate Qt
offscreen import/signal wiring and package manifests. A green source check
does not mean the PC can safely accept the package.

## Installed PC gates: mandatory

1. **Read fresh hashes** of the current `webbie.py`, brain, Whisper
   listener, TTS, socket protocol, memory and voice integration. Preserve
   the existing ~2,300-line custom agent over the shorter GitHub agent.
2. Merge changes into an **owner-local staged copy**, preserving the working
   USB camera device selection, MJPEG format, Qwen3-VL, Natasha, Webbie face,
   STOP/conversation handling, existing persistent memory and live Forage.
   Never use the previously flagged overcurrent webcam cord.
3. Validate required source modules, Qt imports, launcher paths and guarded
   backup/rollback manifest. Do not replace running native workspace files
   without PC-specific checks.
4. With owner present, test read-only health and "Run now"; watch offline
   Ollama failure/recovery; verify desktop quiet hours, sleep, no repeated
   warnings, and no microphone loops.
5. Test one-time, daily, weekly reminder creation, notification, removal,
   service restart deduplication and file mode `0600`. Confirm source 
   upgrades to Study, Studio, Author, Kali Bay, BCN and Media Center still work.
6. Confirm microphone speaker verification remains **fail closed** for
   privileged actions. Separate Cory/Shayna voice authorization and
   consented desktop autopilot are not silently enabled by this upgrade.

**Install status: NOT INSTALLED. This PR is draft until reconciliation.**
