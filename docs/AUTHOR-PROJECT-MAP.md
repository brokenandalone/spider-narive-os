# Author Project Map | October 11, 2026

This upgrade adds a **Project Map** tab to the native Spider OS Author workspace.

The tab displays every chapter from the currently selected book, its current
saved word count, editorial stage (Draft / In revision / Ready), optional word
target, and private scene notes. The filtering box searches chapter titles,
stages, and notes. Open Chapter jumps to the existing chapter editor.

A dedicated SQLite table named chapter_plans keeps **only editorial metadata**.
Its creation is additive. Existing manuscripts, canon notes, chapter snapshots,
book IDs, and story bible records remain intact.

Metadata is autosaved with the existing Author save cycle, and when the user
switches chapters or books. Selecting a new chapter in the Project Map never
changes manuscript prose. Updating a chapter after a review does not silently
mark it Ready, and word targets are optional, not AI-generated.

To test from the repository root:

    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p test_author_project_map.py

Prerequisites: The Author branch sequence through PR #51. This change has its
own pull request and should be merged in dependency order. The first PC install
should back up Documents/Spider OS/Author/library.sqlite3 before source changes.

The Project Map is deliberately local-only and makes no network requests.

Webbie can open it with explicit instructions such as **Webbie, show project map**
or **open the chapter outline**. Those commands must pass the existing
trusted-speaker gate if spoken. They only open this read-only overview while
Author is visible, and do not change chapters or manuscript text.
