"""Local, evidence-aware Story Atlas for Spider Author.

SQLite remains the source of truth. Story facts are explicitly entered by
the writer and are never automatically promoted to canon by an AI.
"""
import hashlib
import re
import sqlite3
from collections import defaultdict


def _clean(value, name, limit=400, required=False):
    if not isinstance(value, str):
        raise ValueError(name + ' must be text.')
    result = value.strip()
    if required and not result:
        raise ValueError(name + ' is required.')
    if len(result) > limit:
        raise ValueError(name + ' exceeds ' + str(limit) + ' characters.')
    return result


def _digest(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _identity(label):
    return re.sub(r'\s+', ' ', label).casefold().strip()


class StoryAtlas:
    ENTITY_KINDS = ('Character', 'Supernatural', 'Place', 'Object', 'Faction')

    def __init__(self, store):
        self.store = store
        self.db = store.db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS atlas_entities(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                kind TEXT NOT NULL DEFAULT 'Character',
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS atlas_events(
                id INTEGER PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books(id),
                chapter_id INTEGER REFERENCES chapters(id),
                story_order INTEGER NOT NULL DEFAULT 0,
                event_key TEXT NOT NULL DEFAULT '',
                when_label TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                evidence_quote TEXT NOT NULL DEFAULT '',
                chapter_digest TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_atlas_events_book
                ON atlas_events(book_id, story_order, id);
            CREATE INDEX IF NOT EXISTS idx_atlas_events_key
                ON atlas_events(event_key);
            CREATE TABLE IF NOT EXISTS atlas_relationships(
                id INTEGER PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books(id),
                source_entity INTEGER NOT NULL REFERENCES atlas_entities(id),
                target_entity INTEGER NOT NULL REFERENCES atlas_entities(id),
                relation TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                CHECK(source_entity <> target_entity)
            );
            CREATE INDEX IF NOT EXISTS idx_atlas_relationships_book
                ON atlas_relationships(book_id);
        """)
        self.db.commit()

    def entities(self):
        return [dict(r) for r in self.db.execute(
            'SELECT * FROM atlas_entities ORDER BY name COLLATE NOCASE, id'
        )]

    def add_entity(self, name, kind='Character', notes=''):
        name = _clean(name, 'Character or place', 120, required=True)
        notes = _clean(notes, 'Entity notes', 12000)
        if kind not in self.ENTITY_KINDS:
            raise ValueError('Unsupported atlas entity category.')
        try:
            with self.db:
                cursor = self.db.execute(
                    'INSERT INTO atlas_entities(name,kind,notes) VALUES(?,?,?)',
                    (name, kind, notes)
                )
        except sqlite3.IntegrityError as error:
            raise ValueError('An atlas entry with this name already exists.') from error
        return cursor.lastrowid

    def relationships(self, book_id):
        self._book(book_id)
        return [dict(r) for r in self.db.execute("""
            SELECT r.*, a.name AS source_name, a.kind AS source_kind,
                   b.name AS target_name, b.kind AS target_kind
              FROM atlas_relationships r
              JOIN atlas_entities a ON a.id=r.source_entity
              JOIN atlas_entities b ON b.id=r.target_entity
             WHERE r.book_id=? ORDER BY r.id
        """, (book_id,))]

    def add_relationship(self, book_id, source_id, target_id, relation, notes=''):
        self._book(book_id)
        relation = _clean(relation, 'Relationship', 120, required=True)
        notes = _clean(notes, 'Relationship notes', 12000)
        if not isinstance(source_id, int) or not isinstance(target_id, int) or source_id == target_id:
            raise ValueError('Choose two different atlas entries.')
        for ident in (source_id, target_id):
            if not self.db.execute(
                'SELECT 1 FROM atlas_entities WHERE id=?', (ident,)
            ).fetchone():
                raise ValueError('A linked atlas entry no longer exists.')
        with self.db:
            cursor = self.db.execute(
                'INSERT INTO atlas_relationships(book_id,source_entity,target_entity,relation,notes) '
                'VALUES(?,?,?,?,?)',
                (book_id, source_id, target_id, relation, notes)
            )
        return cursor.lastrowid

    def _book(self, book_id):
        if not isinstance(book_id, int) or not self.db.execute(
            'SELECT 1 FROM books WHERE id=?', (book_id,)
        ).fetchone():
            raise ValueError('Choose an existing book.')

    def events(self, book_id=None):
        if book_id is not None:
            self._book(book_id)
        sql = """
            SELECT e.*, b.title AS book_title,
                   c.title AS chapter_title
              FROM atlas_events e
              JOIN books b ON b.id=e.book_id
              LEFT JOIN chapters c ON c.id=e.chapter_id
        """
        if book_id is not None:
            sql += ' WHERE e.book_id=?'
        sql += ' ORDER BY e.story_order, e.book_id, e.id'
        return [dict(r) for r in self.db.execute(
            sql, (book_id,) if book_id is not None else ()
        )]

    def upsert_event(self, book_id, title, *, chapter_id=None, story_order=0,
                     event_key='', when_label='', details='', evidence_quote='',
                     event_id=None):
        """Manually save an event; quoted manuscript evidence must match exactly."""
        self._book(book_id)
        title = _clean(title, 'Event title', 200, required=True)
        event_key = _clean(event_key, 'Continuity key', 120)
        when_label = _clean(when_label, 'When label', 120)
        details = _clean(details, 'Event notes', 12000)
        evidence_quote = _clean(evidence_quote, 'Source quote', 2500)
        if (isinstance(story_order, bool) or not isinstance(story_order, int)
                or not -1000000 <= story_order <= 1000000):
            raise ValueError('Story order must be an integer from -1000000 to 1000000.')
        chapter_digest = ''
        if chapter_id is not None:
            chapter = self.store.chapter(chapter_id)
            if chapter['book_id'] != book_id:
                raise ValueError('A source chapter must belong to the selected book.')
            if evidence_quote:
                if evidence_quote not in chapter['content']:
                    raise ValueError('Evidence quote must appear exactly in the selected chapter.')
                chapter_digest = _digest(chapter['content'])
        elif evidence_quote:
            raise ValueError('Evidence requires a source chapter.')
        fields = (
            book_id, chapter_id, story_order, event_key, when_label, title,
            details, evidence_quote, chapter_digest
        )
        with self.db:
            if event_id is None:
                cursor = self.db.execute("""
                    INSERT INTO atlas_events(
                        book_id,chapter_id,story_order,event_key,when_label,title,
                        details,evidence_quote,chapter_digest)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, fields)
                return cursor.lastrowid
            current = self.db.execute(
                'SELECT book_id FROM atlas_events WHERE id=?', (event_id,)
            ).fetchone()
            if current is None or current['book_id'] != book_id:
                raise ValueError('The event does not belong to the selected book.')
            self.db.execute("""
                UPDATE atlas_events SET book_id=?,chapter_id=?,story_order=?,
                    event_key=?,when_label=?,title=?,details=?,
                    evidence_quote=?,chapter_digest=? WHERE id=?
            """, fields + (event_id,))
            return event_id

    def evidence_status(self, event):
        """Returns a conservative, reproducible check, never a canon verdict."""
        if not event['evidence_quote']:
            return 'unanchored'
        if event['chapter_id'] is None:
            return 'unanchored'
        try:
            chapter = self.store.chapter(event['chapter_id'])
        except ValueError:
            return 'missing'
        if chapter['book_id'] != event['book_id']:
            return 'missing'
        if event['evidence_quote'] not in chapter['content']:
            return 'outdated'
        if _digest(chapter['content']) != event['chapter_digest']:
            return 'changed-but-quote-present'
        return 'verified'

    def continuity_audit(self, book_id=None):
        """Check exact anchors and conflicting manually tagged timeline facts.

        A repeated continuity key with different time labels is *possible*
        evidence of a mismatch, not proof of an error. Non-linear plots and
        different points of view may explain the discrepancy.
        """
        events = self.events(book_id)
        checks = []
        verified = 0
        unanchored = 0
        for event in events:
            status = self.evidence_status(event)
            if status == 'verified':
                verified += 1
            elif status == 'unanchored':
                unanchored += 1
            else:
                checks.append({
                    'type': 'evidence',
                    'event_ids': (event['id'],),
                    'message': (f"{event['book_title']} / {event['title']}: "
                                f"evidence is {status.replace('-', ' ')}")
                })
        shared = defaultdict(list)
        for event in events:
            key = _identity(event['event_key'])
            if key and event['when_label']:
                shared[key].append(event)
        for key, entries in sorted(shared.items()):
            labels = {_identity(e['when_label']) for e in entries}
            if len(labels) > 1:
                checks.append({
                    'type': 'timeline',
                    'event_ids': tuple(e['id'] for e in entries),
                    'message': (
                        f"Possible timeline disagreement for '{key}': " +
                        '; '.join(f"{e['book_title']} / {e['title']} "
                                  f"({e['when_label']})" for e in entries)
                    )
                })
        return {
            'events': len(events), 'verified': verified,
            'unanchored': unanchored, 'alerts': checks,
        }
