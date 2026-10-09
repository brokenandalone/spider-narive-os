# Workspace content inside The Web

The Web displays the *real local folders* for each workspace. These are file
manager shortcuts, not copies or syncs. When a folder does not exist the desktop
reports that fact and **does not create a substitute or move private files**.

| Workspace | Local project content |
| --- | --- |
| Author | `~/Documents/Spider OS/Author`, `Originals/` |
| Studio | `~/Documents/Spider Studio`, `~/Music` |
| School | `~/Documents/Spider OS/Study` (matches Study's real data store) |
| Forage | `~/Documents/Spider OS/Research` |
| Deep Forage | `~/Documents/Spider OS/Research/Deep Forage` |
| Art Lab | `~/Pictures`, `~/Documents/Spider OS/Art Lab` |
| Media | `~/Music`, `~/Videos`, `~/Pictures` |
| Kali Bay | `~/Documents/Spider OS/Kali Bay` (the installed container is untouched) |
| Recovery | `~/Documents/Spider OS/Upgrade Backups`, `~/Spider-OS-Backups` |
| Dev Bay | `~/spider-narive-os`, `~/Documents/Spider OS/Dev Bay` |
| Webbie, Communications, System, Games | Local corresponding documents/project folders |

This does **not** scan, duplicate, replace, or publish user files. Application
content still resides in existing native databases, media libraries, repos,
and the Kali Bay container.

## Updating The Web from inside The Web

The installer can be invoked from Konsole in **The Web (X11)**. Save and close
any important work first. The active desktop continues using already-loaded
Python code; after installing, **log out of The Web and sign back into The Web**
to activate the updated shell. Plasma remains a login-screen fallback.
The desktop installer does not import private manuscripts.

## Broken World manuscript and companion import

The separate private archive `Spider-Author-Private-Content-Import.zip`
contains the current verified manuscript through Chapter 16, 20 editable
library entries, future-book planning notes, and original DOCX files.

To import **while using The Web**, extract the private ZIP to a local folder,
open the embedded **Author** tab, choose **Import library**, and select
`Broken-World-Author-Library.json`. The Author editor performs its own save
before the transaction-safe merge. Do not edit the same Author database in
other applications at the same time. Existing library entries aren't
overwritten, and repeated imports of an identical package are skipped.

To preserve the original formatted DOCX documents too, copy the extracted
`Originals` directory to
`~/Documents/Spider OS/Author/Originals` without overwriting anything.
Unlike the on-disk Author JSON bundle, Word formatting isn't represented in
the plain-text editor.

The **command-line** private `import-broken-world.sh --apply` is deliberately
guarded against running while The Web is active, because an embedded Author
window may have unsaved edits. Use the GUI import from The Web rather than
bypassing this guard.

No real SNHU coursework, recordings, private manuscripts, media library, or
Webbie memory is uploaded to public GitHub as part of this release. Their
content must be explicitly imported/copied from its actual owner source.
