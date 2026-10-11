# Spider OS Study: Major coursework upgrade (October 11, 2026)

## Installed baseline

The owner confirmed a full Spider OS installation from October 10, 2026. Treat that as the installed baseline, including yesterday's Study and Webbie upgrades. This pull request is new GitHub source, not an assertion that the October 11 changes are installed. Do not blindly replace installed application files. Respect unknown PC-local changes and preserve the owner's files.

## Features

### Assignment workspaces
Open a selected assignment by double-clicking it or clicking ASSIGNMENT WORKSPACE.
Each assignment has seven editable sections: Instructions, Rubric, Research notes,
Outline, My draft, References, and Feedback. The sections persist in the local
Study database across restarts. Edits auto-save after four seconds of inactivity.
Closing attempts a save and refuses to close if saving fails.

The Check draft button gives a word count, entered reference-line count, and
explicit warnings about missing source placeholders and missing instructions.
It is not an APA verifier, official rubric score, fact checker or grade.

The Work with Webbie button opens the existing Homework Assistant with the
saved assignment instructions, rubric, optional owner notes and draft.
References are explicitly marked unverified. Copying a changed Webbie draft
back into the assignment notebook requires user confirmation, and the
previous draft is snapshotted before replacement.

Export APA Word invokes the existing document generator, requires all
title-page fields, and never overwrites an existing file. The user must verify
every reference and formatting requirement before submitting.

Deleting an assignment now requests confirmation and warns when stored
directions, research or drafts will be removed. Previously saved course
folder files are not removed.

### Course flashcards
The selected course has a manual flashcard deck. Add question/answer cards
or preview and import a CSV with Front,Back or Question,Answer columns.
Duplicate entries are skipped. No SNHU content is scraped.

Reveal an answer, then mark Remembered or Needs practice. Lower-scored cards
are shown first after review. Review counts and cards remain in the local
Study database, not in the school gradebook.

### Native readability
Study now styles table headers and popup menus with contrasting colors.

## Compatibility and privacy

The existing courses, assignments and notes tables are unchanged.
Two optional tables are created with CREATE TABLE IF NOT EXISTS:
assignment_workspaces and flashcards. Course files, Webbie models and
Microsoft OAuth/rclone credentials remain untouched. No auto-upload,
school submission, grading, or login automation occurs.

The coordinated batch installer includes the new Python files. The desktop
installer checks them before altering PC source. It adds missing modules only,
then uses the existing known-baseline reconciliation. Unknown source must
block installation pending review.

## Required PC acceptance

1. Confirm current installed Study code fingerprints and back up the Study
   database at ~/.local/share/spider-os/study/study.db and course Documents.
2. Review the reversible installer preflight; avoid overwriting unrecognized
   Webbie/Study local modifications.
3. Launch Study, double-click an existing assignment and save/reopen each
   section; verify course notes are unchanged.
4. Open a flashcard deck, add/import, reveal answers and check review counts.
5. Request Webbie help; verify no output replaces earlier work unless approved.
6. Export a DOCX and inspect title page, draft, source accuracy and references.
7. Verify SNHU/My SNHU sign-in and school OneDrive separately; account login
   and live syllabus access are NOT established by these code tests.
