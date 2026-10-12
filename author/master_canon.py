"""Explicit, private, revision-tracked canon ledger for Spider Author.

Only writer-approved facts become established canon. The ledger never guesses
a character's history from prose, never invokes a model, and never rewrites a
manuscript. Stored manuscript quotes are verified before acceptance.
"""
import hashlib
import json
import re
from datetime import datetime, timezone


def _text(value, label, limit, required=False):
    if not isinstance(value, str):
        raise ValueError(label + ' must be text.')
    result = value.strip()
    if required and not result:
        raise ValueError(label + ' is required.')
    if len(result) > limit:
        raise ValueError(label + ' is too long.')
    return result


def _digest(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _key(s):
    return re.sub(r'\s+', ' ', s.strip()).casefold()


class MasterCanon:
    STATUSES = ('proposed', 'established', 'superseded')
    CATEGORIES = ('Rule', 'Character', 'Timeline', 'Place', 'Object', 'Faction',
                  'Relationship', 'Plot', 'Other')

    def __init__(self, store):
        self.store = store
        self.db = store.db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS canon_claims(
                id INTEGER PRIMARY KEY,
                book_id INTEGER REFERENCES books(id),
                entity_id INTEGER REFERENCES atlas_entities(id),
                chapter_id INTEGER REFERENCES chapters(id),
                category TEXT NOT NULL,
                fact_key TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                statement TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed'
                    CHECK(status IN ('proposed','established','superseded')),
                source_quote TEXT NOT NULL DEFAULT '',
                source_digest TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_canon_claims_book
                ON canon_claims(book_id, id);
            CREATE INDEX IF NOT EXISTS idx_canon_claims_entity
                ON canon_claims(entity_id);
            CREATE INDEX IF NOT EXISTS idx_canon_claims_key
                ON canon_claims(fact_key);
            CREATE TABLE IF NOT EXISTS canon_claim_history(
                id INTEGER PRIMARY KEY,
                claim_id INTEGER NOT NULL REFERENCES canon_claims(id),
                previous_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.db.commit()

    def _validate_source(self, book_id, chapter_id, source_quote):
        if chapter_id is None:
            if source_quote:
                raise ValueError('A source quote requires a source chapter.')
            return ''
        if isinstance(chapter_id, bool) or not isinstance(chapter_id, int):
            raise ValueError('Invalid chapter identifier.')
        chapter = self.store.chapter(chapter_id)
        if book_id is not None and chapter['book_id'] != book_id:
            raise ValueError('Source chapter belongs to another book.')
        if source_quote and source_quote not in chapter['content']:
            raise ValueError('Source quotation must match saved manuscript exactly.')
        return _digest(chapter['content']) if source_quote else ''

    def _validate_refs(self, book_id, entity_id):
        if book_id is not None:
            self.store.atlas._book(book_id)
        if entity_id is not None:
            if (isinstance(entity_id, bool) or not isinstance(entity_id, int)
                    or not self.db.execute(
                        'SELECT 1 FROM atlas_entities WHERE id=?',
                        (entity_id,)
                    ).fetchone()):
                raise ValueError('Linked entity does not exist.')

    def _normalize(self, book_id, entity_id, chapter_id, category, fact_key,
                   title, statement, status, source_quote):
        self._validate_refs(book_id, entity_id)
        if category not in self.CATEGORIES:
            raise ValueError('Unsupported canon category.')
        if status not in self.STATUSES:
            raise ValueError('Unsupported canon approval status.')
        key = _text(fact_key, 'Fact key', 150)
        title = _text(title, 'Fact title', 200, required=True)
        statement = _text(statement, 'Canon statement', 12000, required=True)
        quote = _text(source_quote, 'Exact source quote', 2500)
        digest = self._validate_source(book_id, chapter_id, quote)
        return (book_id, entity_id, chapter_id, category, _key(key),
                title, statement, status, quote, digest)

    def add(self, title, statement, *, book_id=None, entity_id=None,
            chapter_id=None, category='Rule', fact_key='',
            status='proposed', source_quote=''):
        """Always insert a new claim; promotion is explicit in the desktop UI."""
        fields = self._normalize(
            book_id, entity_id, chapter_id, category, fact_key, title,
            statement, status, source_quote
        )
        with self.db:
            return self.db.execute("""
                INSERT INTO canon_claims(book_id,entity_id,chapter_id,
                category,fact_key,title,statement,status,source_quote,source_digest)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, fields).lastrowid

    def proposed_duplicate(self, *, book_id, chapter_id, title, statement, source_quote):
        """Strict exact-match safeguard for repeated AI suggestions."""
        row = self.db.execute("""
            SELECT id FROM canon_claims
             WHERE status='proposed' AND book_id=? AND chapter_id=?
               AND title=? AND statement=? AND source_quote=?
             LIMIT 1
        """, (book_id, chapter_id, title, statement, source_quote)).fetchone()
        return row['id'] if row else None

    def edit(self, claim_id, *, book_id=None, entity_id=None, chapter_id=None,
             category='Rule', fact_key='', title='', statement='',
             status='proposed', source_quote=''):
        current = self.get(claim_id)
        if current is None:
            raise ValueError('Canon entry no longer exists.')
        fields = self._normalize(
            book_id, entity_id, chapter_id, category, fact_key, title,
            statement, status, source_quote
        )
        with self.db:
            self.db.execute(
                'INSERT INTO canon_claim_history(claim_id,previous_json) VALUES(?,?)',
                (claim_id, json.dumps(current, ensure_ascii=False, sort_keys=True))
            )
            self.db.execute("""
                UPDATE canon_claims
                   SET book_id=?,entity_id=?,chapter_id=?,category=?,fact_key=?,
                       title=?,statement=?,status=?,source_quote=?,source_digest=?,
                       updated_at=CURRENT_TIMESTAMP
                 WHERE id=?
            """, fields + (claim_id,))
        return claim_id

    def get(self, claim_id):
        row = self.db.execute('SELECT * FROM canon_claims WHERE id=?', (claim_id,)).fetchone()
        return dict(row) if row else None

    def history(self, claim_id):
        if self.get(claim_id) is None:
            raise ValueError('Canon entry does not exist.')
        return [dict(row) for row in self.db.execute(
            'SELECT * FROM canon_claim_history WHERE claim_id=? ORDER BY id DESC',
            (claim_id,)
        )]

    def claims(self, *, book_id=None, include_all=False, entity_id=None,
               status=None, query=''):
        if book_id is not None:
            self.store.atlas._book(book_id)
        if status is not None and status not in self.STATUSES:
            raise ValueError('Unsupported canon status.')
        if entity_id is not None:
            self._validate_refs(None, entity_id)
        query = _text(query, 'Search', 150).casefold()
        conditions = []
        args = []
        if not include_all and book_id is not None:
            conditions.append('(c.book_id=? OR c.book_id IS NULL)')
            args.append(book_id)
        if entity_id is not None:
            conditions.append('c.entity_id=?')
            args.append(entity_id)
        if status is not None:
            conditions.append('c.status=?')
            args.append(status)
        sql = """
            SELECT c.*, b.title AS book_title, e.name AS entity_name,
                   ch.title AS chapter_title
              FROM canon_claims c
              LEFT JOIN books b ON b.id=c.book_id
              LEFT JOIN atlas_entities e ON e.id=c.entity_id
              LEFT JOIN chapters ch ON ch.id=c.chapter_id
        """
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
        sql += ' ORDER BY c.category, c.fact_key, c.id'
        rows = [dict(row) for row in self.db.execute(sql, args)]
        if query:
            rows = [row for row in rows if query in (
                ' '.join(str(row[field] or '') for field in (
                    'title','statement','fact_key','category','book_title',
                    'entity_name','source_quote'))
            ).casefold()]
        return rows

    def evidence_status(self, claim):
        if not claim['source_quote'] or claim['chapter_id'] is None:
            return 'unanchored'
        try:
            chapter = self.store.chapter(claim['chapter_id'])
        except ValueError:
            return 'missing'
        if claim['book_id'] is not None and chapter['book_id'] != claim['book_id']:
            return 'missing'
        if claim['source_quote'] not in chapter['content']:
            return 'outdated'
        if _digest(chapter['content']) != claim['source_digest']:
            return 'changed-but-quote-present'
        return 'verified'

    def audit(self, *, book_id=None, include_all=True):
        rows = self.claims(book_id=book_id, include_all=include_all)
        status_counts = {status: sum(c['status'] == status for c in rows)
                         for status in self.STATUSES}
        evidence_counts = {}
        alerts = []
        for claim in rows:
            flag = self.evidence_status(claim)
            evidence_counts[flag] = evidence_counts.get(flag, 0) + 1
            if flag in ('missing','outdated','changed-but-quote-present'):
                alerts.append({
                    'kind': 'evidence', 'ids': (claim['id'],),
                    'message': f"{claim['title']}: source evidence is {flag.replace('-', ' ')}."
                })
        grouped = {}
        for claim in rows:
            if claim['status'] == 'established' and claim['fact_key']:
                grouped.setdefault(claim['fact_key'], []).append(claim)
        for key, group in sorted(grouped.items()):
            different = {_key(c['statement']) for c in group}
            if len(different) > 1:
                alerts.append({
                    'kind':'possible_disagreement',
                    'ids':tuple(c['id'] for c in group),
                    'message': (
                        f"Possible disagreement under key '{key}': " +
                        ' | '.join(c['title'] + ' (' +
                                   (c['book_title'] or 'Global') + ')' for c in group)
                    )
                })
        return {'total':len(rows),'statuses':status_counts,
                'evidence':evidence_counts,'alerts':alerts}
