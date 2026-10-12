# Spider Author: Webbie Canon Intelligence

## Overview

The Canon Intelligence tab is an **explicitly initiated** review of a selected chapter or a complete book against the writer's **Established Master Canon** entries. It uses Webbie's existing local Ollama review engine and never uploads manuscripts to GitHub or automatically rewrites them.

Reviewing an entire book processes every nonempty chapter in bounded segments; it does not silently skip passages. The model is given only up to 12 relevance-ranked approved canon claims per segment to fit local model context. This is a **heuristic shortlist**: absence of flagged issues does not prove consistency.

## Grounding and what is not verified

An AI finding is included only if:

- Its source quotation is an exact substring of the supplied chapter segment, 8 to 240 characters long.
- For possible conflicts, its referenced claim ID matches an actual Established canon entry included in that specific segment's review.
- Its saved source chapter ID, book ID, source offset, end offset, and full-source SHA-256 are recorded.
- Explanations are still interpretations, **not independently verified contradictions**.

Invented quotations and arbitrary claim IDs are discarded. The model output cannot call external commands, edit manuscript prose, change canon status, or inject commands into a privileged tool. User-supplied story text is marked untrusted.

## Controls

**Compare current chapter** or **Compare entire book** starts a local review after saving the current editor. **Cancel review** prevents additional model requests after the active local inference finishes.

Results show **POSSIBLE CONFLICT** or **UNAPPROVED IDEA** with exact citations. **Open verified source** navigates to the source chapter only if the original saved digest still matches.

**Save selected idea as Proposed** is offered only for unapproved suggestions, with an explicit Yes/No confirmation. It verifies source freshness again and saves a normal Master Canon claim with status **Proposed**, never Established. The writer can edit or promote that entry separately in the existing Master Canon tab.

Exact duplicate proposals for the same book, chapter, title, statement, and quotation are blocked, including after reopening the review. Repeated AI suggestions never silently create multiple copies.

The page does not automatically run when opened, including when Webbie opens it by voice. Spoken command **Webbie, show canon intelligence** only switches to the page after trusted-speaker verification. It does not start inference or approve anything.

## Privacy and installation

The new modules are:

- author/canon_intelligence.py: pure review engine / source validation
- author/canon_intelligence_widget.py: Qt background worker and approval user interface

Both are included in the targeted Author installer and the single consolidated Spider OS release manifest. Neither installer contains manuscript documents, the local SQLite file, user authentication data, or Ollama weights. The Author database stays private on the PC. Use the strict preflight and make a separate database backup before upgrading.

This branch is stacked **after PR #79 Master Canon**, itself after #75 Story Atlas, #56 Project Map, #51 Word import and earlier Author dependencies. Merge only after the prerequisites are integrated. Source CI is not a live PC installation.

## Tests

From the repository root:

    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_author_canon_intelligence.py'
    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_author_commands.py'
    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_author_install_manifests.py'

Unit tests use a stub model and disposable library, so a real Ollama server is not needed for CI. Live test with the configured local model is still required after a safe PC install.
