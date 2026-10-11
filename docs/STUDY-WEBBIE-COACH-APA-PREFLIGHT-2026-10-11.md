# Study / Webbie Learning Coach + Offline APA Preflight

## Baseline and source status

**The owner completed a full Spider OS install from October 10, 2026.**
Protect that installed baseline. The October 11 additions in this PR are GitHub
source changes, not installed PC upgrades. This PR is stacked on PR #71, PR #64
and PR #53; integration must preserve working desktop features and local files.

## Webbie tutoring

In Study's Assignments view choose WEBBIE STUDY COACH, or from the selected
assignment's dedicated workspace choose Learn with Webbie.

The tutor loads the selected course and assignment title, displays the user
selected assignment instructions/rubric/research, and provides an editable
text area for owner review. Course notes are unchecked by default. When checked, a scrollable preview displays the selected notes for review. Nothing is
sent to the local Webbie brain until the owner chooses Ask Webbie.

Five modes use the **existing, installed Webbie local Ollama backend**:
- Explain a concept with examples and a check-for-understanding question.
- Socratic follow-up, one guided question at a time.
- Five-question practice quiz with a clearly separate answer key.
- Structured study guide with definitions and memory cues.
- Up to twelve flashcards in Q:/A: format for review.

The owner can ask follow-ups in the same window. Short-lived session history
is held in memory until the dialog closes or the owner presses
Clear tutoring history. The owner can copy the answer to their clipboard or
explicitly save a private TXT transcript. Transcript files do not overwrite
existing files and are limited to 250 KB; no automatic transcript save occurs.
For flashcards, every proposed Q:/A: card is displayed in a confirmation
preview, and saving is optional. No model-generated cards are silently stored.

An Ollama connection or AI model is NOT provisioned by this PR. The owner PC
must confirm that the existing Webbie service can answer. No new background
listener or cloud account is used. The tutor does not change existing
assignments, submit to SNHU or claim official quiz scores.

## Citation and APA preflight

A dedicated APA and source preflight button in the assignment notebook
analyzes only owner-entered draft text and the workspace References section.
It reports likely in-text surname/year matches, potential missing references,
duplicate reference lines, unsupported source placeholders and general Word
formatting checks. The report is a conservative regular-expression heuristic,
not a source resolver or APA certification. Organizational authors,
multiple authors and nonstandard references may be incorrectly flagged or
missed. Verify every reference against real sources.

An APA Word export with no entered references, unresolved placeholders or
possible unmatched citations displays a warning before allowing continued
export of a draft. The user can decline without any file changes or proceed
to save the draft, still manually verifying citations. The existing no-clobber
DOCX exporter remains in place.

## Source files and installation

New Python files:
- study/study_coach.py
- study/study_coach_ui.py
- study/apa_preflight.py

Modified:
- study/study.py, study/assignment_workspace_ui.py
- system/release_batch.py, the-web/package/install-desktop.sh
- tests/test_study_batch_release.py

Run exact-head Python regression tests and native Qt smoke tests, plus the
existing release and desktop smoke checks. The guarded one-batch release must
recognize the installed Study source version or stop; no unrecognized files
should be overwritten. Back up the Study database and coursework before any
PC installation.

## PC acceptance

1. Confirm the October 10 installed source hashes and create a verified,
   private Study backup outside the course folder.
2. Open Study, choose PSY-328 or SOC-112 (only if those user-entered courses
   exist) and open a local assignment, without creating fake deadlines.
3. Launch the coach; verify unselected course notes stay excluded,
   and opt-in shows the source notes in a preview before the local AI request,
   different tutoring modes work, the local backend responds, and errors
   leave the coursework intact.
4. Save a private tutoring TXT transcript, then try the same filename and
   confirm the earlier saved content is not replaced.
5. Generate flashcards, decline confirmation once, then review and
   approve selected cards, and verify that only approved cards are saved.
5. Enter example references and a draft, run the offline preflight, confirm
   citation warnings are advisory and do not alter anything.
6. Try APA export with an unmatched reference; decline and confirm no file
   was written, then manually review an export.
7. Confirm no SNHU submission, OneDrive upload, or Webbie system settings
   were changed. SNHU and school OneDrive authentication require actual
   owner-PC verification, not GitHub source checks.
