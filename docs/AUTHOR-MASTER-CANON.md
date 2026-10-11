# Spider OS Author: Broken World Master Canon

## Purpose

Master Canon is a separate, local-only tab within the native Author workspace. It tracks official world rules, characters, places, objects, plot facts, and relationships across novels. It complements (but never replaces) the existing Canon notes, Story Bible, Project Map, Story Atlas, and full-book AI review.

## The editorial rule

- **Proposed**: a concept that should not yet be treated as authoritative.
- **Established**: explicitly approved by the writer in a confirmation dialog.
- **Superseded**: retained for historical reference, not the current canon.

No content is automatically promoted from drafts, manuscripts, Webbie, or old notes. Adding a new entry opens in Proposed status. Promoting a claim to Established asks for explicit confirmation. Editing a claim saves the previous complete record in canon_claim_history. Rather than deleting history, mark outdated claims Superseded.

## What it can link

One claim may have a global scope or one book, an optional Story Atlas character/entity, and one optional source chapter. A verbatim source quote is accepted only when it appears in the currently saved chapter. The stored chapter SHA-256 makes later revisions visible without rewriting prose.

The Master Canon tab offers a searchable table, scope filter, status filter, and Character/Entity Dossier picker. A dossier brings together linked claims across books. Open Source Chapter navigates across books; quotation highlighting occurs only if the current chapter text still matches the stored digest.

## Checks and limitations

The conservative review counts proposed, established and superseded claims; verifies or flags exact manuscript quotations; and finds **possible disagreements** where two established claims share a normalized fact key but have different statements. It never rules that a flashback or disputed account is wrong. Entries without linked source quotations are labeled unanchored, not false or verified.

**No completeness claims:** only manually entered ledger claims are evaluated. The large-text AI review remains a separate, explicitly requested action. Old Canon notes and Story Bible entries are preserved but are NOT automatically imported or declared Established. No hidden web requests or character biography generation.

## Webbie command

With existing trusted-voice authorization active, say "Webbie, show master canon" or "open the character dossiers". This opens the dashboard only; it cannot approve or edit canon.

## Protected release integration

New modules author/master_canon.py and author/master_canon_widget.py are included in the targeted Author/Webbie installer and the combined Spider OS release manifest. SQLite adds new tables only when the upgraded Author app starts. The Author database under ~/Documents/Spider OS/Author/ stays outside both install manifests and the public repository. Keep your private backup and use the existing strict preflight and rollback procedure before installation.

The branch is stacked after Story Atlas PR #75, Project Map #56, DOCX #51, and their preceding Author feature chain. CI passing is not equivalent to merging or installing anything on the Spider OS computer.

From the repository root, run:

    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_author_master_canon.py'
    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_author_install_manifests.py'
    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_author_commands.py'

