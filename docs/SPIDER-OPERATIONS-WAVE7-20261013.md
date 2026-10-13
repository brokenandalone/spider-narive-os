# Spider OS Wave 7 | Operations Hub

**Status: SOURCE DEVELOPMENT ONLY. Not installed or activated on the owner PC.**

## Purpose

Add an owner-click-only cross-workspace interface without replacing the
recently installed Webbie/JARVIS, desktop shell, Kali Bay GUI, Studio, Author,
Study, Forage, or Nova source.

This feature branch is based on the October 12 source inventory. The owner's
October 13 live PC contains private later merges and remains authoritative.
**Never deploy this source branch as a full OS tree.** Merge only these new,
additive files into the owner's verified combined source before any install.

## New capabilities

- A single screen with explicit buttons to open the existing Studio, Author,
  Study, Forage, Deep Forage and Kali Bay applications.
- Studio WAV sample-quality preflight for PCM WAV recordings (bounded first/last
  2 seconds); peak, RMS, sample-rate, channel count and potential full-scale
  samples. No audio processing or playback.
- Studio folder-level stems preflight (up to 24 WAV tracks) for mismatched
  sample rates and bit depths, duration spread, and sampled peak warnings.
  Does not mix, synchronize, rewrite or play stems.
- Author TXT/Markdown structural review with approximate word count, chapter
  headings and editorial placeholders. No manuscript or canon mutation.
- Author folder-level chapter overview (up to 60 local text chapters), with
  word totals, placeholders and empty chapter signals. No recursive scanning.
- Study TXT/Markdown draft checklist with optional word-range directions,
  simple citation-pattern counts, placeholder flags and references heading.
- Study draft-folder review (up to 50 local text assignments), with aggregated
  word counts, unresolved source markers and references headings.
  No source checking, grading, or APA certification.
- Deep Forage saved-source JSON metadata inspection: host diversity, duplicate
  exact URLs, missing titles and publication dates. Never connects to URLs.
- Kali Bay readiness and Purple executable checks using the existing
  read-only Kali Bay operations. Does not provision or start a container.
- Spider OS read-only service and source-presence summary with optional,
  explicitly chosen 0600 JSON report export.

## Safety and activation

- No automatic operations. Buttons require direct local owner clicks.
- This code never touches GRUB/cryptodisk, Ubuntu packages, model files, voice
  selection, mic/camera, Kali container packages, Nova or BCN.
- No generic shell execution, text-to-command conversion, or AI task grants.
- It does not silently upload the user's manuscripts or research to GitHub.
- Reports contain aggregate metadata only; the GUI displays no raw private text.
- Save is explicit, private (mode 0600), exclusive-create only.
- The new GUI launcher uses PyQt5. Defer real-device rendering and activation
  tests until the owner wants to test the broader upgrade round.
- The Web desktop is **not** launched as a second shell.
- This work is not a media player or radio upgrade.

## Files added

- system/operations_quality.py
- system/operations_services.py
- system/operations_hub.py
- system/operations_batch.py
- system/bin/spider-operations
- distro/config/applications/spider-operations.desktop
- tests/test_operations_hub.py
- tests/test_operations_batch.py

## Future release checklist

1. Reconcile with the owner PC's current **168 installed application-source
   changes**, including Kali viewport repair and Natasha's edge-tts environment.
2. Run full integrated source tests and Qt offscreen checks on the final combined
   source. Run manual workspace, audio and GUI tests later as requested.
3. Audit the existing desktop launch commands and screen scaling on the actual
   machine; this branch does not modify live window layout.
4. Produce a single backup-first, hash-pinned installer with rollback,
   treating today’s installed source as the baseline. Owner explicitly approves.
5. Activate only after verification, without automatic reboot/service restart.
