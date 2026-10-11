# Spider OS Study: Course Reading Library

## Installed baseline

The owner confirmed a full October 10, 2026 Spider OS installation. All October 11 source upgrades are stacked draft PRs and NOT installed yet. Never overwrite unrecognized installed Study, Webbie or other workspace changes. Preserve school credentials, user documents and AI models.

## New owner-selected reading workflow

Open an existing course, choose COURSE READINGS, and explicitly import a TXT, Markdown, Word DOCX or text PDF file. The importer makes a private local copy in that course's Readings folder, preserving the original. It validates a maximum 8 MB source, reads up to 12,000 characters with the existing course_materials parser, and records SHA-256 digest plus bounded excerpt in an additive course_readings SQLite table. Duplicate contents are skipped. Same filename with different content gets a new non-clobbering filename. File copies are owner-only with incomplete copies removed on failure.

Search the indexed, user-selected documents by keyword inside the current course. The results display document titles, excerpts and ranking by token matches. This is intentionally keyword search, not full-book AI retrieval or verified academic research.

From Webbie Study Coach or Webbie Homework, choose Select a saved course reading. A preview dialog requires explicit approval before the reading excerpt is placed into the assistant's editable materials text field. This is a separate step from clicking Ask Webbie or Write draft; no automatic model call, upload, school account access, submission, or inferred bibliographic citation occurs.

This library never crawls school OneDrive, never auto-downloads the syllabus, does not do OCR for scanned PDFs, and never assumes that a partial extract is a complete chapter. PDF support requires pdftotext on the owner PC.

## Source and QA

Adds study/reading_library.py and study/reading_library_ui.py plus an additive SQLite table. Wires the owner-controlled picker to Study, Webbie Homework and Webbie Study Coach. Both modules are included in the shared guarded batch release and desktop installer preflight. Pure regression and offscreen Qt tests cover deduplication, no clobber, source preservation, course separation, failure cleanup, explicit preview and Webbie controls.

## Acceptance before deployment

1. Verify the installed October 10 source fingerprints and preserve local changes.
2. Back up the private Study database and course documents outside their directories.
3. Import a document and verify the original is unchanged; repeat import and check deduplication.
4. Check course isolation, local keyword search, new copy permissions and restart persistence.
5. From Webbie Homework or Tutor decline a reading handoff, then opt in and inspect the excerpt before a separate model request.
6. Confirm actual SNHU and Microsoft account sign-in separately. Source tests cannot establish those.
