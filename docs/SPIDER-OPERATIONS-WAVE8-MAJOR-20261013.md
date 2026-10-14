# Spider OS Wave 8 | Major Multi-Workspace Expansion

**Status: SOURCE WORK COMMITTED ONLY. Uninstalled, unactivated and not yet acceptance-tested.**

## Scope and continuity

This change builds on Wave 7's Spider Operations Hub and does **not**
replace any existing live Webbie, The Web, Author, Study, Studio, Kali Bay,
Forage, Deep Forage, or native Nova implementation.

**Critical:** Branches Wave 7 and Wave 8 descend from an October 12 source
snapshot that predates 168 application-source file writes on the owner PC on
October 13, plus Natasha TTS/Kali viewport hotfix work. Do not git-checkout
and install this repository tree over the owner's local install. During the
next approved release, copy/reconcile only the new Wave 7/8 additive modules
and the explicitly reviewed Hub launcher additions.

The owner explicitly deferred hands-on acceptance testing. The test files
exist as future verification steps; no live-Pc test/upgrade success is claimed.

## Seven substantive capability tracks

### 1. Spider Studio recording-production readiness
- Explicitly selected local folder, max 24 WAV stems.
- Format mismatch, sampled peak, duration spread and suggested instrument roles
  based only on filenames. No generated audio or mixing changes.
- Never claims mastering, true peak, stem alignment or genuine voice identity.

### 2. Author / Broken World continuity coverage
- Explicitly selected chapter folder (up to 60 TXT/Markdown files) **and**
  user-created JSON character alias list (1-80 canonical names).
- Reports chapter-level *literal character-name coverage*, not invented canon
  contradictions, motives, ages, supernatural rules or dates.
- Does not replace Author's Master Canon or alter chapters.
- Example **structure only**, not canonical data:
  {"characters":{"Example Character":["Example Character","Example"]}}

### 3. Study / SNHU rubric preflight
- Explicitly selected text/Markdown draft and rubric, max 2 MiB each.
- Identifies up to 40 checklist headings, signals possible topic overlap,
  counts unresolved source placeholders and references heading.
- Does not grade coursework, validate citations, certify APA or submit work.

### 4. Forage / Deep Forage offline provenance
- Explicitly selected Markdown report and sources JSON, up to 1000 sources.
- Citation marker coverage, duplicate normalized URLs, website host diversity,
  missing title/date and citations out of range.
- No browsing, external requests, source retrieval or truth claims.

### 5. Kali Bay / Purple training
- Uses only existing read-only Kali Bay readiness and installed executable
  inventory for five authorized training tracks.
- Tool guidance for traffic capture, harmless sample triage, host baseline
  review, offline intrusion detection, and audit logs.
- Does not execute Kali scanners, start sensors or provision packages.

### 6. System / Recovery snapshots and drift
- Fingerprints existing source files from a fixed allowlist without scanning
  private documents.
- Explicitly saved snapshot reports can later be selected for a changed/missing
  file comparison (no automatic rollback).
- Counts only backup directory names in an explicitly selected parent folder,
  **not** backup integrity or actual restorability.

### 7. Webbie / local model inventory
- Reads resident service status, key module presence and local Ollama model
  names. Does not send model prompts or download models.
- Explicitly does not modify installed qwen3:8b, Natasha/Matilda, wake/STOP,
  microphone, camera, permitted speakers or computer-control access.

## GUI

A new **Wave 8** tab inside the separate Operations Hub adds nine owner-click
operations. Two independently selected file/folder inputs where required.
Long local reviews use a worker thread with bounded scope; they cannot be
dispatched by a webpage, model, TV audio or microphone.
The existing Operations Hub manual report export is the only save route.

## Files

- system/operations_wave8_core.py
- system/operations_wave8_studio.py
- system/operations_wave8_author.py
- system/operations_wave8_study.py
- system/operations_wave8_research.py
- system/operations_wave8_kali.py
- system/operations_wave8_system.py
- system/operations_wave8_webbie.py
- system/operations_wave8_ui.py
- system/operations_hub.py (only additive GUI wiring)
- tests/test_operations_wave8.py
- docs/SPIDER-OPERATIONS-WAVE8-MAJOR-20261013.md
- system/wave8_release_manifest.json

## Deferred release and acceptance

1. Preserve protected installed files byte-for-byte, including the latest
   Webbie voice, Kali Bay viewport, Studio, desktop shell and all personal data.
2. Freeze exact Git SHAs and inspect current live PC file hashes.
3. Run unit tests, Python compile, offscreen Qt launch, slow/broken file
   handling, Webbie isolation and source/build continuity tests.
4. Carry out hands-on Studio, Author, Study, Forage, Kali and Webbie acceptance
   only when owner resumes tests.
5. Do not count this source development as an install or a new OS version.
6. Do not package Media Center, BCN website, mobile OS, Ubuntu, or bootloader
   changes into this native-application proposal.
