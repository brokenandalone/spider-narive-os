"""Per-book audiobook bookmarks in the existing private Author database.

Bookmarks hold only a source fingerprint and a section cursor, not manuscript
text. Resume is refused if any chapter changed since the bookmark was saved.
"""
import hashlib
import json


def book_fingerprint(chapters):
    manifest = [
        [int(chapter["id"]), str(chapter["title"]),
         hashlib.sha256(str(chapter["content"]).encode("utf-8")).hexdigest()]
        for chapter in chapters
    ]
    return hashlib.sha256(
        json.dumps(manifest, separators=(",", ":"), ensure_ascii=False)
        .encode("utf-8")).hexdigest()


class NarrationBookmarks:
    def __init__(self, store):
        self.store = store
        self.db = store.db
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS narration_bookmarks(
                    book_id INTEGER PRIMARY KEY REFERENCES books(id),
                    book_hash TEXT NOT NULL,
                    chapter_id INTEGER NOT NULL,
                    section_index INTEGER NOT NULL CHECK(section_index >= 0),
                    updated TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now'))
                )
            """)

    def save(self, book_id, book_hash, chapter_id, section_index):
        if not isinstance(book_hash, str) or len(book_hash) != 64:
            raise ValueError("Invalid audiobook source fingerprint.")
        if int(section_index) < 0:
            raise ValueError("Invalid audiobook section.")
        row = self.db.execute(
            "SELECT 1 FROM chapters WHERE id=? AND book_id=?",
            (chapter_id, book_id)).fetchone()
        if not row:
            raise ValueError("Book and chapter do not match.")
        with self.db:
            self.db.execute(
                "INSERT INTO narration_bookmarks("
                "book_id,book_hash,chapter_id,section_index,updated) "
                "VALUES(?,?,?,?,strftime('%Y-%m-%d %H:%M:%f','now')) "
                "ON CONFLICT(book_id) DO UPDATE SET book_hash=excluded.book_hash,"
                "chapter_id=excluded.chapter_id,section_index=excluded.section_index,"
                "updated=excluded.updated",
                (book_id, book_hash, chapter_id, int(section_index)))

    def get(self, book_id):
        return self.db.execute(
            "SELECT * FROM narration_bookmarks WHERE book_id=?",
            (book_id,)).fetchone()

    def is_current(self, bookmark, chapters):
        return (bookmark is not None and
                bookmark["book_hash"] == book_fingerprint(chapters) and
                any(ch["id"] == bookmark["chapter_id"] for ch in chapters))

    def clear(self, book_id):
        with self.db:
            self.db.execute(
                "DELETE FROM narration_bookmarks WHERE book_id=?", (book_id,))
