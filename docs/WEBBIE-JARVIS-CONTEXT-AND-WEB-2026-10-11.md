# Webbie Jarvis desktop awareness and web control — October 11, 2026

**SOURCE ONLY — NOT INSTALLED.** This draft PR stacks on the October 11
proactive-monitoring PR #61, voice-correction PR #54 and October 10 combined
release PR #49. Do not merge branches out of order or overwrite the
customized resident Webbie on the owner's computer.

## Implemented behavior

### Browser and webpage requests
Webbie recognizes **direct** typed or spoken requests:

- "Webbie open YouTube"
- "Webbie go to github.com"
- "Webbie open https://www.wikipedia.org/wiki/Music"
- "Webbie search the web for seven-string guitar recording tips"
- "Webby open snhu.edu"

The router is deterministic. It uses explicit HTTPS addresses or a small
built-in alias map, or generates a URL-encoded Google search. It **does not**
ask the language model what command to run, pass model output to the control
socket, execute shell fragments, or open file/javascript/network-admin URLs.
Direct IP addresses, local hostnames, embedded credentials, nonstandard ports
and non-HTTPS schemes are rejected.

**Owner-granted operation:** The Web's Computer Control dialog now has a URL
field and an **Open approved website** button. The owner chooses an actual
installed WebBrowser desktop app, authorizes the short-lived task through the
existing visible consent process, and confirms **each exact URL**. The local
bridge receives `WEB:<canonical HTTPS URL>` but cannot create permissions;
the GUI checks the selected app/grant again. Navigation is handed to the
**system default browser**, which may differ from the selected WebBrowser.
A request reports "open requested," not proof the page loaded. The desktop
operator's STOP revokes the grant. Typed requests only stage a proposal.

There is no background browser automation, unsolicited click, password entry,
hidden browser control, browser-history scraping, or background site crawling.

### Desktop-aware conversation

A new GUI-owned temporary context handoff shares:

- Currently selected Spider OS workspace and assistant mode.
- User-visible selected title, such as a song, chapter or assignment title.
- The exact owner-selected authorized window title, **only** when a live
  Computer Control grant exists and that window was explicitly bound.
- The owner's approved computer task, only while that grant is active.

The record is atomically written to private `0600` local status, expires in
90 seconds unless the GUI refreshes it, and drops task/window details when
Webbie goes to sleep. It does **not** save screen images, captured webpage
text, audio or camera observations. Source/provenance and expiration are
checked on read. It is advisory information only, never voice identity,
independent user consent or authority to click/type/send/delete.

The resident agent uses this context for "Webbie, what am I working on?"
or "what workspace am I in?" and passes bounded advisory context to the
local Ollama prompt for ordinary follow-ups. The temporary context is never
copied into Webbie's long-term memory or used to generate a tool command.
Screen inspection itself **still** requires the explicit one-window GUI
consent and local vision worker already in the source. A selected window
title is not proof Webbie can see its live pixels.

### Voice handoff reliability

The resident listener now checks wake/stop phrases using a normalized
comparison but preserves the original recognized command for routing. URL
punctuation, paths, `?` and query strings survive. Webbie and Webby aliases
are present in source defaults and fallback configuration. Commands inside
page content are not considered direct user voice commands.

### Existing controlled computer operation

Computer Control already contains approved installed-app launch, exact-window
selection and focus, single screenshot inspection, window-confined reviewed
pointer/key/text actions, STOP and short supervised navigation autopilot.
This upgrade **extends** those mechanisms; it does not silently expand them
to arbitrary full-device control or claim that external app automation has
been demonstrated on the installed PC. The per-speaker trusted Cory/Shayna
microphone identity gate is still not connected. Speech transcription is not
authentication. Sensitive actions remain on-screen decisions.

## Test suite

```bash
python3 -m unittest discover -s tests -p 'test_webbie_jarvis_browser.py' -v
python3 -m unittest discover -s tests -p 'test_webbie_jarvis_context.py' -v
python3 -m unittest discover -s tests -p 'test_webbie_jarvis_gui.py' -v
python3 -m unittest discover -s tests -p 'test_webbie_jarvis_wake.py' -v
```

Release manifest `system/release_batch.py` and read-only
`tools/combined_release_audit.py` include the new files. CI success
validates source in a runner, not the PC's audio, X11 session, browser,
window geometry, Qwen models, microphone, active camera or private memories.

## PC acceptance gates

1. Snapshot latest custom agent/brain, TTS/Whisper, active local model,
   KDE/X11 state, working camera MJPEG configuration, face/sleep controls,
   memory and consent rules. Preserve installed enhancements absent from
   the shorter GitHub agent.
2. Reconcile new modules into a **private staged copy** and run the
   complete single-release audit. Do not write into live
   `/usr/local/lib/spider-os` before the user's one coordinated install.
3. Test Webbie/Webby wake and STOP, exact URLs, quoted punctuation,
   browser selection and on-screen approval, denied unauthorized URLs,
   existing installed-app routing, and STOP revocation on the actual PC.
4. Test spoken and typed workspace follow-ups, selected task/window expiry,
   sleep erasure and local model responses. Verify no screenshots leak into
   disk-based context and no long-term memory entries were created from it.
5. Run full regression checks for Author, Studio, Study, Forage, Kali Bay,
   Nova/BCN Media, native The Web desktop and backup rollback.
6. Do not test with the previously flagged electrically unsafe USB webcam
   cord. Never force-delete or overwrite the owner's schoolwork, manuscripts,
   live services, or trained voice samples.

**Status: Draft GitHub source, not installed, real PC acceptance pending.**
