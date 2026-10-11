# Author Workspace: safe Word manuscript import

Author is its own native Spider OS workspace, separate from Spider Studio.

## What's new

- **Import DOCX** on the Author toolbar opens a local Word manuscript.
- The preview shows the book title, chapter count, word count, and chapter headings before any database changes.
- A Word paragraph styled **Heading 1** creates a chapter. Text before the first heading becomes **Front Matter**. Documents without Heading 1 become one complete **Manuscript** chapter. Table-cell text in the document body is included.
- Confirmed imports create a new book transactionally. Existing manuscripts and canon notes are never replaced. Duplicate imports are prevented by SHA-256 fingerprint; changing the file after preview aborts import.
- The original Word file is not modified or uploaded.

## Limits

This is a **text import, not a lossless Word conversion**. Word formatting, images, comments, tracked changes, footnotes, headers, and page layout are not reliably preserved. Review your source file and keep it. DOCX size is limited to 50 MB; main-document XML is capped at 30 MB.

DOCX export, EPUB, PDF, snapshots, library backups, full-book reviews, and Webbie audiobook bookmarking remain separate existing features.

## Testing and branch

Run: python3 -m unittest discover -s tests -p test_author_docx_import.py

The upgrade stacks on feature/author-cross-book-continuity-ledger-20261010. Merge prerequisite Author pull requests first. Tests use synthetic manuscripts and temporary libraries, not actual private books.
