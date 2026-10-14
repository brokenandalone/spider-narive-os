# Spider OS Wave 9 | Local Music, One-Frame Vision, Canon and Desktop

**Source development only. No live installation or test/acceptance claim.**

This branch is based on Wave 8 commit e9c523a996e2c86cf39d7434df5e2623c9ad97a4, which predates newer private Oct 13 live PC changes. Never deploy the full repository tree over the live installation. Reconcile only the additive Wave 7-9 modules and reviewed Hub wiring with the owner PC.

## Local music generation
- Reuses the existing Studio music_backend LocalMusicClient and SongRequest.
- Preview original song or instrumental, 1-2 takes, 10-600 seconds.
- Owner clicks Generate, confirms a dialog, and chooses a real local output folder.
- Existing ACE-Step client handles versioned WAV outputs, manifests, local endpoint checks and stop-waiting status. The local engine must already be running. Nothing auto-installs an engine/model or contacts Suno.
- Stop waiting does not guarantee that ACE-Step cancels a server-side job.

## One-frame local vision
- Reuses existing Webbie camera capture and local Ollama visual inference.
- One webcam frame or one primary-screen JPEG snapshot requires a fresh GUI approval every time.
- The image is processed locally in memory and is not automatically saved.
- Vision description may contain sensitive screen details; owner must review before optional report export.
- No unattended camera monitoring, automatic desktop actions, face/voice identification, web upload or resident Webbie changes.

## Source-anchored Broken World canon checks
- Select approved-claims JSON, proposed-claims JSON and up to 60 text chapters.
- Claim JSON schema: spider-canon-claims-v1; each claim has entity, attribute, scope, value, status; proposals may include source_file and source_quote.
- Flag only potential differing values for the same entity, property and scope.
- Compare exact source quotes against manually selected chapter files.
- No manuscript edits, new lore, canonical changes or automatic acceptance.

## The Web
- Audit fixed installed desktop launchers for Studio, Author, Study, Forage, Deep Forage and Kali Bay.
- Do not open a second desktop shell, change KDE settings or activate an app automatically.

## GUI / controls
- New Wave 9 tab inside existing Spider Operations Hub, divided into Studio AI, Webbie Vision, Author Canon and The Web sections.
- Qt worker thread for long tasks, max one active action; Hub refuses to close during ongoing worker activity.
- Results appear in the UI. Export remains owner-initiated via the existing Save Summary control.
- No automatic model downloads, security scans, uploads or Webbie permission grants.

## Files
- New system/wave9_music.py, system/wave9_visual.py, system/wave9_canon.py, system/wave9_desktop.py, system/wave9_ui.py.
- New tests/test_wave9_creative_vision.py with test cases for owner approval, safe outputs, canon scoping, source quotes, and launcher audit.
- New docs/SPIDER-OPERATIONS-WAVE9-20261013.md and system/wave9_release_manifest.json.
- Additive tab wiring in system/operations_hub.py, no changes to the resident agent, Studio backend, or the native desktop shell.

## Release gates deferred at user request
1. Read current owner PC hashes. Preserve working Webbie/qwen3:8b/Natasha, Studio, Kali viewport, Nova, The Web and personal data.
2. Run unit tests, syntax checks, Qt offscreen and security boundary tests on the FINAL reconciled candidate.
3. Explicit consent/manual hardware acceptance for ACE-Step render, webcam, screen, canon and desktop when owner resumes testing.
4. Back up and verify a guarded, rollback-capable one-batch release. Do not install without owner approval.
5. Ubuntu/bootloader, Media Center/BCN website and Spider OS Mobile remain separate project/release scopes.
