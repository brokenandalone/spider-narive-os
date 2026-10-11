# Kali Bay Lab Guides and Private Reports
Date: October 11, 2026

This is a **draft, source-only** upgrade stacked on Kali Bay Command Center PR #60. It builds on the existing Kali Distrobox, read-only Kali Purple checks, saved favorites and Webbie socket rather than replacing them.

## Added to Kali Bay
- **LAB GUIDES** is the fifth native tab. Search eight offline defensive workflows covering authorized asset inventory, packet-capture triage, web application review, suspicious-file handling, host hardening, Kali Purple alert triage, incident evidence recording and remediation verification.
- Every guide offers a *read-only* checklist that explicitly asks about authorization and scope. **CREATE NOTEBOOK FROM GUIDE** is an explicit, confirmed action that creates a new private local notebook and populates it with a saved template. It does not install a Kali package, run a command, scan the network or contact Webbie.
- Existing **LAB NOTES** now has **EXPORT SAVED REPORT**. Reports contain only the last saved lab revision, a clear evidence-verification disclaimer and reviewer checklist. If there are unsaved changes, export does not proceed.
- Files are Markdown under `~/.local/share/spider-os/kali-bay/projects/reports/`, with mode 0600 and a private 0700 report directory. Export names contain only generated lab IDs, numeric revisions and UTC timestamps. Repeated exports create distinct files with exclusive creation; no outside file path or name is accepted.
- The selective Kali-only installer source manifest now covers `kali-bay/runtime/lab_reports.py` and compiles it in preflight.

## Core safety guarantees
The guides and report builder are local Python code with no subprocess, network or resident-AI clients. Notes are never sent automatically, and reports are not uploaded. They are *user-authored notes*, not automatically verified security findings. Imported evidence bytes and scans are out of scope; existing Kali tools retain their explicit launches. Webbie speaker authorization is not changed.

## Validation
```bash
bash -n kali-bay/bin/kali-bay
bash -n kali-bay/package/install-kali-bay.sh
python3 -m py_compile kali-bay/ui/kali_bay.py kali-bay/runtime/lab_reports.py kali-bay/runtime/workspace_store.py
python3 -m unittest discover -s tests -p 'test_kali_lab_reports.py' -v
python3 -m unittest discover -s tests -p 'test_*.py'
bash kali-bay/package/install-kali-bay.sh --check
```

## Installation continuity
**Not installed, not merged.** This branch depends on PR #60 -> #50 -> #46 and must be rebased/reconciled into the current guarded Spider OS combined release source. The new `lab_reports.py` must be included in the combined manifest or native Kali Bay will fail to import it. Inspect and back up the owner-customized Kali UI before any installation. Run a complete owner-PC staged test after the GitHub source tests pass. Do not force-merge or reinstall Kali or Webbie just to apply these additions.
