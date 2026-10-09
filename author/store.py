"""Transactional, local manuscript storage. No network or automatic rewrites."""
import sqlite3
from pathlib import Path


class AuthorStore:
    def __init__(self, root=None):
        self.root = Path(root or Path.home() / 'Documents' / 'Spider OS' / 'Author')
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'library.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                canon TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS chapters(id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL
                REFERENCES books(id), title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, chapter_id INTEGER NOT NULL
                REFERENCES chapters(id), content TEXT NOT NULL, created TEXT NOT NULL DEFAULT
                (strftime('%Y-%m-%d %H:%M:%f','now')));
        ''')
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS story_bible(
                id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL REFERENCES books(id),
                category TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS companion_references(
                id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL REFERENCES books(id),
                category TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
                source_name TEXT NOT NULL DEFAULT '');
            CREATE INDEX IF NOT EXISTS idx_story_bible_book ON story_bible(book_id);
            CREATE INDEX IF NOT EXISTS idx_companion_book ON companion_references(book_id);
        """)
        self.db.commit()

    def books(self):
        return self.db.execute('SELECT * FROM books ORDER BY id').fetchall()

    def create_book(self, title):
        if not title.strip():
            raise ValueError('A book needs a title.')
        with self.db:
            return self.db.execute('INSERT INTO books(title) VALUES(?)', (title.strip(),)).lastrowid

    def chapters(self, book_id):
        return self.db.execute('SELECT * FROM chapters WHERE book_id=? ORDER BY id', (book_id,)).fetchall()

    def create_chapter(self, book_id, title, content=''):
        if not title.strip():
            raise ValueError('A chapter needs a title.')
        with self.db:
            return self.db.execute('INSERT INTO chapters(book_id,title,content) VALUES(?,?,?)',
                                   (book_id, title.strip(), content)).lastrowid

    def chapter(self, chapter_id):
        row = self.db.execute('SELECT * FROM chapters WHERE id=?', (chapter_id,)).fetchone()
        if row is None:
            raise ValueError('Chapter does not exist.')
        return row

    def save(self, chapter_id, content):
        # The old version and replacement commit together, or neither commits.
        with self.db:
            old = self.chapter(chapter_id)['content']
            if content == old:
                return
            self.db.execute('INSERT INTO snapshots(chapter_id,content) VALUES(?,?)', (chapter_id, old))
            self.db.execute('UPDATE chapters SET content=? WHERE id=?', (content, chapter_id))

    def snapshots(self, chapter_id):
        return self.db.execute('SELECT * FROM snapshots WHERE chapter_id=? ORDER BY id DESC',
                               (chapter_id,)).fetchall()

    def restore(self, chapter_id, snapshot_id):
        row = self.db.execute('SELECT content FROM snapshots WHERE id=? AND chapter_id=?',
                              (snapshot_id, chapter_id)).fetchone()
        if row is None:
            raise ValueError('Snapshot does not belong to this chapter.')
        self.save(chapter_id, row['content'])
        return row['content']

    def canon(self, book_id):
        row = self.db.execute('SELECT canon FROM books WHERE id=?', (book_id,)).fetchone()
        if row is None:
            raise ValueError('Book does not exist.')
        return row['canon']

    def save_canon(self, book_id, content):
        with self.db:
            self.db.execute('UPDATE books SET canon=? WHERE id=?', (content, book_id))

    def import_text(self, book_id, path):
        path = Path(path)
        if path.suffix.lower() not in {'.txt', '.md', '.markdown'}:
            raise ValueError('Import TXT or Markdown. Open office manuscripts in Writer.')
        # Imports create new chapters and never modify the original file.
        return self.create_chapter(book_id, path.stem, path.read_text(encoding='utf-8-sig'))

    def backup(self, path):
        path = Path(path)
        if path.resolve() == (self.root / 'library.sqlite3').resolve():
            raise ValueError('Choose a separate backup file.')
        with sqlite3.connect(path) as target:
            self.db.backup(target)

    def close(self):
        self.db.close()

    def import_bundle(self, path):
        """Merge an Author JSON bundle once per source, without overwriting books."""
        import hashlib
        import json
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        if payload.get('format') != 'spider-author-1' or not isinstance(payload.get('books'), list):
            raise ValueError('Not a Spider Author bundle.')
        added = 0
        with self.db:
            self.db.execute('CREATE TABLE IF NOT EXISTS imported_sources(fingerprint TEXT PRIMARY KEY)')
            for book in payload['books']:
                fingerprint = hashlib.sha256(json.dumps(book, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if self.db.execute('SELECT 1 FROM imported_sources WHERE fingerprint=?', (fingerprint,)).fetchone():
                    continue
                if not isinstance(book.get('title'), str) or not book['title'].strip():
                    raise ValueError('Invalid book title.')
                cursor = self.db.execute('INSERT INTO books(title,canon) VALUES(?,?)',
                    (book['title'], book.get('canon', '')))
                book_id = cursor.lastrowid
                for chapter in book['chapters']:
                    if not isinstance(chapter.get('title'), str) or not isinstance(chapter.get('content'), str):
                        raise ValueError('Invalid chapter content.')
                    self.db.execute('INSERT INTO chapters(book_id,title,content) VALUES(?,?,?)',
                        (book_id, chapter['title'], chapter['content']))
                self.db.execute('INSERT INTO imported_sources VALUES(?)', (fingerprint,))
                added += 1
        return added

    # These additions never overwrite or restructure imported manuscript rows.
    BIBLE_CATEGORIES = (
        'Canon', 'Character', 'Location', 'Timeline', 'Rule',
        'Relationship', 'Plot Thread', 'Theme', 'Research'
    )

    def story_entries(self, book_id):
        return self.db.execute(
            'SELECT * FROM story_bible WHERE book_id=? ORDER BY id', (book_id,)
        ).fetchall()

    def add_story_entry(self, book_id, category, title, body=''):
        if category not in self.BIBLE_CATEGORIES or not title.strip():
            raise ValueError('A supported category and title are required.')
        with self.db:
            return self.db.execute(
                'INSERT INTO story_bible(book_id,category,title,body) VALUES(?,?,?,?)',
                (book_id, category, title.strip(), body)
            ).lastrowid

    def save_story_entry(self, entry_id, category, title, body):
        if category not in self.BIBLE_CATEGORIES or not title.strip():
            raise ValueError('A supported category and title are required.')
        with self.db:
            cursor = self.db.execute(
                'UPDATE story_bible SET category=?,title=?,body=? WHERE id=?',
                (category, title.strip(), body, entry_id)
            )
            if cursor.rowcount != 1:
                raise ValueError('Story Bible entry not found.')

    def references(self, book_id):
        return self.db.execute(
            'SELECT * FROM companion_references WHERE book_id=? ORDER BY id',
            (book_id,)
        ).fetchall()

    def add_reference(self, book_id, title, category='Reference', body='', source_name=''):
        if not title.strip():
            raise ValueError('Companion reference title required.')
        with self.db:
            return self.db.execute(
                'INSERT INTO companion_references(book_id,category,title,body,source_name) VALUES(?,?,?,?,?)',
                (book_id, category, title.strip(), body, source_name)
            ).lastrowid

    def save_reference(self, reference_id, title, category, body, source_name=''):
        if not title.strip():
            raise ValueError('Companion reference title required.')
        with self.db:
            cursor = self.db.execute(
                'UPDATE companion_references SET title=?,category=?,body=?,source_name=? WHERE id=?',
                (title.strip(), category, body, source_name, reference_id)
            )
            if cursor.rowcount != 1:
                raise ValueError('Companion reference not found.')

    def rename_chapter(self, chapter_id, title):
        if not title.strip():
            raise ValueError('A chapter needs a title.')
        with self.db:
            cursor = self.db.execute(
                'UPDATE chapters SET title=? WHERE id=?', (title.strip(), chapter_id)
            )
            if cursor.rowcount != 1:
                raise ValueError('Chapter not found.')

    def word_count(self, book_id=None):
        rows = self.db.execute(
            'SELECT content FROM chapters WHERE book_id=?', (book_id,)
        ) if book_id is not None else self.db.execute('SELECT content FROM chapters')
        return sum(len(row['content'].split()) for row in rows)

    @staticmethod
    def _search_term(text):
        if not isinstance(text, str):
            raise ValueError('Search needs text.')
        text = text.strip()
        if not text:
            return None
        if len(text) > 200:
            raise ValueError('Search is too long.')
        return '%' + text.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'

    def search_library(self, text, book_id=None, limit=100):
        """Read-only search of chapters, Story Bible, companion references and canon."""
        pattern = self._search_term(text)
        if not pattern:
            return []
        limit = max(1, min(int(limit), 200))
        results = []
        for kind, table, body_col in (
            ('chapter', 'chapters', 'content'),
            ('story', 'story_bible', 'body'),
            ('reference', 'companion_references', 'body')
        ):
            sql = (
                f"SELECT b.id AS book_id, b.title AS book_title, "
                f"t.id AS item_id, t.title AS title, t.{body_col} AS body "
                f"FROM {table} t JOIN books b ON b.id=t.book_id "
                f"WHERE (t.title LIKE ? ESCAPE '!' OR t.{body_col} LIKE ? ESCAPE '!')"
            )
            params = [pattern, pattern]
            if book_id is not None:
                sql += " AND b.id=?"
                params.append(book_id)
            sql += " ORDER BY t.id LIMIT ?"
            params.append(limit)
            for row in self.db.execute(sql, params):
                body = row['body']
                found = body.casefold().find(text.strip().casefold())
                results.append({
                    'kind': kind, 'book_id': row['book_id'],
                    'book_title': row['book_title'], 'item_id': row['item_id'],
                    'title': row['title'],
                    'excerpt': body[max(0, found-55):max(0, found-55)+190].replace('\\n', ' ')
                })
                if len(results) >= limit:
                    return results
        sql = "SELECT id,title,canon FROM books WHERE (title LIKE ? ESCAPE '!' OR canon LIKE ? ESCAPE '!')"
        params = [pattern, pattern]
        if book_id is not None:
            sql += " AND id=?"
            params.append(book_id)
        for row in self.db.execute(sql, params):
            results.append({
                'kind': 'book/canon', 'book_id': row['id'], 'book_title': row['title'],
                'item_id': row['id'], 'title': row['title'], 'excerpt': row['canon'][:190]
            })
            if len(results) >= limit:
                break
        return results
