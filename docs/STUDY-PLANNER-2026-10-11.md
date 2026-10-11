# Study school planner upgrade (October 11, 2026)

This is a **source-only**, reviewable change stacked on the Studio + School feature branch. It has **not** signed into SNHU or school OneDrive, imported real assignments, modified school accounts, or changed the owner's installed Spider OS PC.

## Added

- Selected-course assignment CSV import from a file the owner explicitly picks; supported headings are `Title,Due,Status`, `Assignment,Due Date`, or `Title,Deadline`. Dates use strict `YYYY-MM-DD` or are blank.
- Preview and explicit confirmation before importing. Existing assignment title/date pairs and repeated CSV rows are skipped; completed rows are ignored rather than silently reopened. Up to 500 entries and 512 KB per CSV.
- All-course `.ics` calendar export for **open, dated assignments only**, suitable for manual import into a chosen calendar app. No automatic calendar event creation, browser scraping, OneDrive access, or SNHU submission.
- Private atomic calendar writes; existing calendar files are never replaced without confirming in Study. No migration or deletion of existing coursework or folders.
- Dashboard counts assignments due today and in the next seven days. Invalid/undated values remain visible instead of guessed.

## Example CSV

```csv
Title,Due,Status
Module Seven Project,2026-10-18,Open
Module Eight Discussion,2026-10-25,Open
Notes to review,,Open
```

Dates shown above are **illustrative**, not SNHU deadlines.

## Acceptance checklist

1. Test source unit tests, import of CSV with BOM, malformed dates, duplicates and completed rows.
2. Test the Study UI with a selected course. Confirm that cancelling a preview adds nothing.
3. Confirm current local assignments and notes survive installation and that a completed assignment does not appear in the exported calendar.
4. Open exported calendar in the installed preferred calendar app; manually confirm before importing calendar events.
5. Sign into SNHU and school OneDrive on the PC independently, then test explicit downloads and uploads. No automatic sync is implied.
6. Integrate through the existing reversible combined installer only after reconciling PC-local Study changes.

This feature does not store passwords, transfer school data without consent, or claim access to actual SNHU assignment deadlines.
