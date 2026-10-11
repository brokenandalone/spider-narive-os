# Spider Author Story Atlas, October 11, 2026

Privacy-first upgrade to the native Author workspace.

## Story Atlas: Timeline

Create a manually entered chronological event, numeric order and optional story-time label (e.g. Night 1, 3:13).
Optionally link it to an existing chapter in the selected book and copy an **exact quotation**. Author refuses an invented source quote, and stores a digest of the source chapter for later checks.
A repeated optional continuity key (e.g. 313-receipt) can link the same event across novels.
Events can be edited and source chapters opened. No manuscript prose is automatically rewritten.

## Character Network

Create Character, Supernatural, Place, Object or Faction entries shared by the local library, then connect any two with a writer-defined relationship in the current book.
The native Qt graph displays relationship lines and names. Do not treat the visual as an AI-generated claim about your characters. Entries and links require explicit writer approval.

## Continuity Checks

- Checks exact source quotes against saved chapters. Differentiates verified, unanchored, outdated, and changed-but-quote-present evidence.
- Compares time labels of manually tagged events that share a continuity key, inside a book or across selected books.
- Labels conflicting labels as **possible** timeline disagreements. Flashbacks and unreliable narrators may be intentional.
- Makes no claim of completeness for untagged manuscript passages; zero findings do not prove full consistency.
- Runs locally and never uploads manuscripts or story secrets to GitHub.

## Webbie and author control

Trusted Author voice users can say "Webbie, show story atlas" or "open the character network". Existing speaker verification still applies. This merely opens the Story Atlas; voice commands cannot create characters, rewrite chapters, or assert canon.

## Installation and tests

New source modules: author/story_atlas.py and author/atlas_widget.py.
Both targeted Author/Webbie and combined Spider OS installer manifests include them, and no manuscript/user database paths.
The branch stacks on PR #56. Merge the Author dependency chain first. Back up your Author SQLite library before installing; do not deploy partial modules.

Unit tests: test_author_story_atlas.py, test_author_install_manifests.py, test_author_commands.py.
CI success validates the GitHub source, not the live Spider OS PC installation.

## Graphical chronology

The Timeline tab includes a horizontal, selectable chronology strip that follows numeric story order. Clicking an event marker highlights the exact event row for editing or opening its source chapter. The strip displays up to 160 events for responsive drawing; the full saved chronology is always present in the table below. Red markers indicate missing or outdated evidence; verified quotes use purple markers.
