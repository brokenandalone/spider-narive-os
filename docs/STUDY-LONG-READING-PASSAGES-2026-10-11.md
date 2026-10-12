# Spider OS Study: Long Reading Passage Search

## Installed baseline, scope, and release gates

The owner confirms a **full October 10, 2026 Spider OS installation**. The October 11 Study upgrades are still staged on GitHub in stacked draft PRs. They are not installed on the owner's PC simply because source tests pass.

This PR builds on Course Reading Library PR #77 and Study Coach PR #73. Keep unknown local Study, Webbie, Studio and system customizations intact; require installed-file fingerprint reconciliation before the next **single coordinated system-wide installation**.

## New features

- **Longer local reading index:** Explicitly imported TXT, Markdown, DOCX and text PDFs are now parsed to at most 240,000 characters instead of indexing only the opening 12,000. The original 8 MB document file cap remains unchanged. Image-only scans are not automatically OCR'd.
- **Searchable passages:** Each imported document is segmented into approximately 3,200-character passages with 220 characters of overlap, capped at 90 passages. Every passage preserves extraction-order index and original extracted-text character offsets.
- **Deep keyword search:** Search by topic within the selected course. Results identify the matching passage and can expose material that appeared far past the old first 12,000 characters.
- **Browse and preview:** The course Reading Library has Browse passages, which lists passages from a selected reading, plus a preview window. The user must explicitly choose the passage that is copied into Webbie Homework or Webbie Study Coach.
- **Evidence provenance:** Owner-selected material includes its document filename, extraction passage number and character offsets. The preview explicitly states these numbers **are not PDF/book page numbers or bibliographic citations**. This adds traceability without inventing APA references.
- **Legacy safety:** Older course reading records are not silently reimported or overwritten. The owner can select Expand older index to parse the existing local copied document, but the copied file's SHA-256 must still match its original saved digest. Reindexing is atomic and opt-in.

## Storage and compatibility

- New SQLite table: course_reading_passages with foreign key cascade to existing course_readings records; original tables, notes, assignments, flashcards, scores and documents are unchanged.
- Import copies remain new, private 0600-permission files. Text passages are stored in the private Study database. Import/expansion validates bounded characters, passage indices, offsets and exact recorded hash, then commits atomically.
- Legacy read_course_document callers retain the existing 12,000-character default. Only explicit library import and reindex invoke its 240,000-character maximum.
- The shared single-batch release and desktop installer gain study/reading_passages.py. All unknown installed source modifications must block overwrite.
- No background indexing, account scraping, school submission, network searches, AI hallucinated page numbers, automatic cloud transfer or claims of source verification.

## Required owner-PC acceptance

1. Confirm installed October 10 source fingerprints and save verified private backups of Study database and course documents.
2. Import an existing long reading through Study, then search for a phrase appearing later than 12,000 characters.
3. Confirm the matched passage number, character offsets, and a correct preview.
4. Decline the transfer confirmation and prove nothing appears in Webbie's prompt. Then approve the exact passage and observe it in editable context before separately invoking the local model.
5. Choose an older 12K-only imported reading, reindex it, and ensure existing records, drafts, notes and flashcards remain.
6. Alter a disposable test copy and confirm the digest mismatch blocks reindex.
7. Inspect the exported paper separately for APA validity. Source passage labels are never references.
8. Verify the guarded batch installation and rollback and separately check live My SNHU / school OneDrive access on the actual PC.

This is extended **local keyword retrieval**, not a complete academic search engine, full textbook comprehension, automatic PDF page extraction, or an installed owner-PC capability.
