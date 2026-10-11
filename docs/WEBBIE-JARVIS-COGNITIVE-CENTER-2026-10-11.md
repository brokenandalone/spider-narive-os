# Webbie Jarvis: Cognitive Control Center
## Major Webbie source upgrade · October 11, 2026

**DRAFT CODE ONLY. NOT INSTALLED ON THE OWNER'S SPIDER OS PC.**
Stack dependency: PR #49 guarded source staging → PR #54 voice correction
→ PR #61 proactive+reminders → PR #67 browser/context → PR #68 navigation
→ this cognitive source PR. Do not merge or install out of order.

### Added: local owner-curated task memory and next steps

`webbie/brain/focus_tasks.py` stores up to 48 explicitly owner-entered
tasks in a private `0600` JSON file. Every task contains a Spider OS
workspace, short project title, owner-entered next step, and
active/paused/done status. Tasks never run programs or modify documents;
a task title and next step are DATA, not commands or proof of authorization.
Private sessions suppress injecting this persistent task store into
new-model prompts. Webbie can read the current workspace's active task,
and the local Ollama system prompt gets a bounded advisory task label
only outside private sessions. Tasks have explicit on-screen add, edit,
pause, resume, mark done, and delete controls in the dedicated Focus dialog.

### Added: actual local AI readiness and model inventory

`webbie/brain/local_model_inventory.py` only reads
`http://127.0.0.1:11434/api/tags` and `/api/ps` and checks whether the
owner's configured brain/vision model is present. The GUI runs these
read-only requests on a Qt worker so it does not block the desktop.
It reports installed tags, which ones Ollama reports loaded, and whether
the model names configured in Spider OS can be found. It does not infer
response quality, select/switch models, initiate downloads, enable cloud AI,
or run generation. Existing installed Qwen and Gemma settings remain
authoritative. A false/offline reading is reported, not replaced with an
invented success.

### Added: Webbie private sessions

The new cognitive dialog exposes Start/End Private Session, with an
explicit confirmation and a `0600` owner-local preference file.
It is OFF by default, preserving existing Webbie behavior until selected.
When ON, the repository chat engine does not read or write its recent
conversation file or long-term memory; automatic remembering is blocked;
explicit "remember that ..." commands do not save data. The agent avoids
writing new `last_heard` / `last_reply` snippets into its status JSON
while private. You can separately click **Clear recent conversation**
with its own confirmation. Existing long-term memories are preserved.
This is a local privacy feature, NOT secure deletion, an incognito
OS/browser mode, suppression of Ollama's internal caches or control over
other Spider OS workspaces' logs.

### Added: cognitive control panel and emergency privacy controls

`the-web/shell/webbie_cognitive_center.py` offers a single
purple-themed UI for owner focus tasks, background-read local model
inspection, private session status, clearing the recent chat and a
"STOP computer control and camera" request. Sensitive changes require
direct local GUI clicks, not voice text/model/page/screen commands.
Importantly, when Webbie goes to sleep in The Web, it now revokes
current Computer Control grants, stops the selected camera workflow,
and clears ephemeral screen observations. Background proactive checks
and Webbie's service are not stopped by this UI action.

### Voice correction and contextual reasoning

The single-worker `VoiceTurnCoordinator` now **invalidates the old
turn generation immediately** when a new correction is queued, rather
than permitting a slow old answer to resume after a newer command.
It also invokes the existing interruptible TTS stop callback. Only
the last of multiple queued corrections is retained; model work itself
still exits at its normal timeout and corrections can expire. No
parallel unmanaged model workers are spawned.

The resident agent understands read-only "what is my focus?",
"what should I work on next?", "private session status" and similar
questions. No voice command starts/deletes tasks, toggles privacy,
changes model choice, or grants desktop actions. Existing CORy/Shayna
speaker verification remains unresolved and fails closed for
privileged action adapters. Model-generated content and untrusted
screen/webpage/room descriptions cannot grant permissions.

### Source testing

```bash
python3 -m unittest discover -s tests -p test_webbie_focus_tasks.py -v
python3 -m unittest discover -s tests -p test_webbie_privacy_controls.py -v
python3 -m unittest discover -s tests -p test_webbie_local_model_inventory.py -v
python3 -m unittest discover -s tests -p test_webbie_cognitive_center.py -v
python3 -m unittest discover -s tests -p test_webbie_voice_queue.py -v
python3 tools/combined_release_audit.py --help
```

The source integration manifest (`system/release_batch.py`) and
read-only release audit now list every new Python module. The tests
must also be run against the current owner's installed code before
any GUI/service replacement.

### Protected single-install PC reconciliation

1. Gather fresh hashes and compare the actual 2000+ line customized
   installed `webbie/agent/webbie.py`, Ollama config, memory/Whisper,
   Natasha TTS, camera MJPEG capture, KDE X11, face/sleep visual, Webbie
   panel, Media Center/Nova, Study, Author, Studio, Kali Bay and Forage.
2. Apply all NEW changes into a private **staging** tree without
   overwriting the owner's longer installed resident agent, current
   memories, models, trained voices, source documents, pictures or keys.
   No Linux OS/boot/login/USB-camera reconfiguration is part of this PR.
3. Test focused tasks per workspace, privacy mode across GUI/voice,
   read-only Ollama online/offline, guided navigation, desktop STOP,
   wake/STOP interruption, sleep cancelling grants, model fallback
   failures, and session-specific stale context.
4. Check full release manifest and rollback hash match, then carry out
   **one approved coordinated owner installation**, if gates pass.
5. Never stress or power-cycle the previously flagged faulty webcam
   USB cable. Verify safety with the working hardware arrangement only.

**GitHub CI success is not live-PC acceptance. This draft contains no
OS deployment and makes no promises of full Jarvis autonomy.**
