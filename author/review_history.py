"""Local history for completed Webbie editorial reviews.

Reports live in the Author SQLite database so normal Author backups include
them. Reports never replace or modify manuscript chapters. Historical reviews
are preserved and marked outdated when reviewed sources change.
"""
import hashlib
import json


def digest(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


class ReviewHistory:
    def __init__(self, store):
        self.store = store
        self.db = store.db
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS review_reports(
                    id INTEGER PRIMARY KEY,
                    book_id INTEGER NOT NULL REFERENCES books(id),
                    scope TEXT NOT NULL CHECK(scope IN ('chapter','book')),
                    depth TEXT NOT NULL CHECK(depth IN ('quick','deep')),
                    manifest_json TEXT NOT NULL,
                    report TEXT NOT NULL,
                    created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_review_reports_book
                    ON review_reports(book_id,id DESC);
            """)

    def manifest(self, book_id, chapters, canon):
        known = {c["id"]: c for c in self.store.chapters(book_id)}
        entries = []
        for chapter in chapters:
            if chapter["id"] not in known:
                raise ValueError("Chapter does not belong to selected book.")
            entries.append({
                "id": int(chapter["id"]), "title": str(chapter["title"]),
                "sha256": digest(chapter["content"])
            })
        if not entries or len({c["id"] for c in entries}) != len(entries):
            raise ValueError("Review must contain distinct chapters.")
        return {"chapters": entries, "canon_sha256": digest(canon)}

    def save(self, book_id, scope, depth, report, manifest):
        if scope not in ("book", "chapter") or depth not in ("quick", "deep"):
            raise ValueError("Invalid review settings.")
        if not isinstance(report, str) or not report.strip() or len(report) > 10_000_000:
            raise ValueError("Review report is empty or too large.")
        if not isinstance(manifest, dict) or not isinstance(manifest.get("chapters"), list):
            raise ValueError("Invalid review manifest.")
        if scope == "chapter" and len(manifest["chapters"]) != 1:
            raise ValueError("Chapter review must refer to exactly one chapter.")
        for chapter in manifest["chapters"]:
            row = self.db.execute("SELECT book_id FROM chapters WHERE id=?",
                                  (chapter["id"],)).fetchone()
            if row is None or row["book_id"] != book_id:
                raise ValueError("Review chapter no longer belongs to book.")
        payload = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
        with self.db:
            return self.db.execute(
                "INSERT INTO review_reports(book_id,scope,depth,manifest_json,report) "
                "VALUES(?,?,?,?,?)", (book_id, scope, depth, payload, report)
            ).lastrowid

    def list(self, book_id, limit=40):
        return self.db.execute(
            "SELECT id,book_id,scope,depth,manifest_json,created "
            "FROM review_reports WHERE book_id=? ORDER BY id DESC LIMIT ?",
            (book_id, max(1, min(int(limit), 100)))
        ).fetchall()

    def get(self, report_id, book_id):
        row = self.db.execute(
            "SELECT * FROM review_reports WHERE id=? AND book_id=?",
            (report_id, book_id)).fetchone()
        if row is None:
            raise ValueError("No saved review found for this book.")
        return row

    def is_current(self, report):
        try:
            manifest = json.loads(report["manifest_json"])
            recorded = manifest["chapters"]
            current = self.store.chapters(report["book_id"])
            if report["scope"] == "chapter":
                expected_ids = {c["id"] for c in recorded}
                current = [c for c in current if c["id"] in expected_ids]
            observed = [
                {"id": int(ch["id"]), "title": str(ch["title"]),
                 "sha256": digest(ch["content"])} for ch in current
            ]
            return (observed == recorded and
                    digest(self.store.canon(report["book_id"])) ==
                    manifest["canon_sha256"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def chapters_for_report(self, report):
        """Return present chapters linked by stable ID, never guessed from AI prose."""
        manifest = json.loads(report["manifest_json"])
        current = {c["id"]: c for c in self.store.chapters(report["book_id"])}
        return [
            {"id": item["id"], "title": current[item["id"]]["title"]}
            for item in manifest["chapters"] if item["id"] in current
        ]
