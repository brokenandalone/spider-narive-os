#!/usr/bin/env python3

import re
import sqlite3
from pathlib import Path


DATA_DIR = (
    Path.home()
    / ".local"
    / "share"
    / "spider-os"
    / "study"
)

DB_PATH = DATA_DIR / "study.db"

DOCUMENTS_ROOT = (
    Path.home()
    / "Documents"
    / "Spider OS"
    / "Study"
)


class StudyStore:
    def __init__(self):
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        DOCUMENTS_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.db = sqlite3.connect(
            DB_PATH
        )

        self.db.row_factory = (
            sqlite3.Row
        )

        self.db.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.create_schema()

    def create_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                due TEXT DEFAULT '',
                status TEXT DEFAULT 'Open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(course_id)
                    REFERENCES courses(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notes (
                course_id INTEGER PRIMARY KEY,
                content TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(course_id)
                    REFERENCES courses(id)
                    ON DELETE CASCADE
            );

            -- Additive storage. No existing coursework is changed or migrated.
            CREATE TABLE IF NOT EXISTS assignment_workspaces (
                assignment_id INTEGER PRIMARY KEY,
                instructions TEXT NOT NULL DEFAULT '',
                rubric TEXT NOT NULL DEFAULT '',
                research TEXT NOT NULL DEFAULT '',
                outline TEXT NOT NULL DEFAULT '',
                draft TEXT NOT NULL DEFAULT '',
                "references" TEXT NOT NULL DEFAULT '',
                feedback TEXT NOT NULL DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                correct INTEGER NOT NULL DEFAULT 0,
                incorrect INTEGER NOT NULL DEFAULT 0,
                last_review TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(course_id, front, back)
            );
            CREATE TABLE IF NOT EXISTS assignment_scores (
                assignment_id INTEGER PRIMARY KEY,
                earned TEXT NOT NULL,
                possible TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(assignment_id) REFERENCES assignments(id)
                    ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                minutes INTEGER NOT NULL CHECK(minutes BETWEEN 1 AND 600),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS assignment_steps (
                id INTEGER PRIMARY KEY,
                assignment_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                due TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
                UNIQUE(assignment_id, title)
            );
            CREATE TABLE IF NOT EXISTS assignment_sources (
                id INTEGER PRIMARY KEY,
                assignment_id INTEGER NOT NULL,
                reference TEXT NOT NULL,
                locator TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
                UNIQUE(assignment_id, reference)
            );
            """
        )

        self.db.commit()

    def ensure_default_course(self):
        count = self.db.execute(
            "SELECT COUNT(*) FROM courses"
        ).fetchone()[0]

        if count == 0:
            self.add_course(
                "General Study"
            )

    def courses(self):
        return self.db.execute(
            """
            SELECT id, name
            FROM courses
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()

    def add_course(self, name):
        name = name.strip()

        if not name:
            return None

        cursor = self.db.execute(
            """
            INSERT INTO courses(name)
            VALUES(?)
            """,
            (name,),
        )

        self.db.commit()

        self.course_folder(
            cursor.lastrowid
        )

        return cursor.lastrowid

    def remove_course(self, course_id):
        self.db.execute(
            """
            DELETE FROM courses
            WHERE id = ?
            """,
            (course_id,),
        )

        self.db.commit()

    def course(self, course_id):
        return self.db.execute(
            """
            SELECT id, name
            FROM courses
            WHERE id = ?
            """,
            (course_id,),
        ).fetchone()

    def course_folder(self, course_id):
        course = self.course(
            course_id
        )

        if not course:
            return DOCUMENTS_ROOT

        safe = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            course["name"],
        ).strip("_")

        if not safe:
            safe = (
                f"Course_{course_id}"
            )

        folder = (
            DOCUMENTS_ROOT
            / safe
        )

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        (folder / "Assignments").mkdir(
            exist_ok=True
        )

        (folder / "Notes").mkdir(
            exist_ok=True
        )

        (folder / "Resources").mkdir(
            exist_ok=True
        )

        (folder / "Research").mkdir(
            exist_ok=True
        )

        return folder

    def assignments(self, course_id):
        return self.db.execute(
            """
            SELECT
                id,
                title,
                due,
                status
            FROM assignments
            WHERE course_id = ?
            ORDER BY
                CASE
                    WHEN status = 'Complete'
                    THEN 1
                    ELSE 0
                END,
                due,
                title
            """,
            (course_id,),
        ).fetchall()

    def add_assignment(
        self,
        course_id,
        title,
        due="",
    ):
        title = title.strip()
        due = due.strip()

        if not title:
            return

        self.db.execute(
            """
            INSERT INTO assignments(
                course_id,
                title,
                due
            )
            VALUES(?, ?, ?)
            """,
            (
                course_id,
                title,
                due,
            ),
        )

        self.db.commit()

    def add_assignments_bulk(self, course_id, rows):
        """Insert a confirmed batch atomically with no schema or folder changes."""
        if not self.course(course_id):
            raise ValueError("Selected course does not exist.")
        values = [(course_id, title, due) for title, due in rows]
        with self.db:
            self.db.executemany(
                "INSERT INTO assignments(course_id, title, due) VALUES (?, ?, ?)",
                values,
            )
        return len(values)

    def set_assignment_status(
        self,
        assignment_id,
        status,
    ):
        self.db.execute(
            """
            UPDATE assignments
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                assignment_id,
            ),
        )

        self.db.commit()

    def delete_assignment(
        self,
        assignment_id,
    ):
        self.db.execute(
            """
            DELETE FROM assignments
            WHERE id = ?
            """,
            (assignment_id,),
        )

        self.db.commit()

    def get_notes(
        self,
        course_id,
    ):
        row = self.db.execute(
            """
            SELECT content
            FROM notes
            WHERE course_id = ?
            """,
            (course_id,),
        ).fetchone()

        if not row:
            return ""

        return row["content"]

    def save_notes(
        self,
        course_id,
        content,
    ):
        self.db.execute(
            """
            INSERT INTO notes(
                course_id,
                content,
                updated_at
            )
            VALUES(
                ?,
                ?,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT(course_id)
            DO UPDATE SET
                content = excluded.content,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                course_id,
                content,
            ),
        )

        self.db.commit()

    def assignment_record(self, assignment_id):
        return self.db.execute(
            "SELECT a.id, a.course_id, a.title, a.due, a.status, c.name AS course "
            "FROM assignments a JOIN courses c ON c.id=a.course_id "
            "WHERE a.id = ?", (assignment_id,),
        ).fetchone()

    def get_assignment_workspace(self, assignment_id):
        fields = ("instructions", "rubric", "research", "outline", "draft",
                  "references", "feedback")
        if self.assignment_record(assignment_id) is None:
            raise ValueError("Assignment does not exist.")
        record = self.db.execute(
            'SELECT instructions, rubric, research, outline, draft, "references", '
            'feedback FROM assignment_workspaces WHERE assignment_id=?',
            (assignment_id,),
        ).fetchone()
        return {name: record[name] if record else "" for name in fields}

    def save_assignment_workspace(self, assignment_id, values):
        fields = ("instructions", "rubric", "research", "outline", "draft",
                  "references", "feedback")
        if self.assignment_record(assignment_id) is None:
            raise ValueError("Assignment was deleted before saving.")
        if set(values) != set(fields):
            raise ValueError("The assignment workspace fields are incomplete.")
        for name in fields:
            value = values[name]
            if (not isinstance(value, str) or len(value) > 120000
                    or "\x00" in value):
                raise ValueError("Invalid assignment section: " + name)
        with self.db:
            self.db.execute(
                'INSERT INTO assignment_workspaces '
                '(assignment_id, instructions, rubric, research, outline, draft, '
                '"references", feedback) VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
                'ON CONFLICT(assignment_id) DO UPDATE SET '
                'instructions=excluded.instructions, rubric=excluded.rubric, '
                'research=excluded.research, outline=excluded.outline, '
                'draft=excluded.draft, "references"=excluded."references", '
                'feedback=excluded.feedback, updated_at=CURRENT_TIMESTAMP',
                (assignment_id,) + tuple(values[name] for name in fields),
            )

    def flashcards(self, course_id):
        return self.db.execute(
            "SELECT id, course_id, front, back, correct, incorrect, last_review "
            "FROM flashcards WHERE course_id=? ORDER BY id", (course_id,),
        ).fetchall()

    def add_flashcards(self, course_id, cards):
        if not self.course(course_id):
            raise ValueError("Course does not exist.")
        checked = []
        for front, back in cards:
            if (not isinstance(front, str) or not isinstance(back, str)
                    or not front.strip() or not back.strip()
                    or len(front) > 1500 or len(back) > 1500
                    or "\x00" in front or "\x00" in back):
                raise ValueError("Invalid flashcard contents.")
            checked.append((course_id, front.strip(), back.strip()))
        with self.db:
            previous = self.db.total_changes
            self.db.executemany(
                "INSERT OR IGNORE INTO flashcards(course_id, front, back) "
                "VALUES (?, ?, ?)", checked)
            return self.db.total_changes - previous

    def record_flashcard_review(self, card_id, correct):
        with self.db:
            cursor = self.db.execute(
                "UPDATE flashcards SET correct=correct+?, incorrect=incorrect+?, "
                "last_review=CURRENT_TIMESTAMP WHERE id=?",
                (1 if correct else 0, 0 if correct else 1, card_id),
            )
            return cursor.rowcount == 1

    def delete_flashcard(self, course_id, card_id):
        with self.db:
            self.db.execute(
                "DELETE FROM flashcards WHERE course_id=? AND id=?",
                (course_id, card_id),
            )

    def assignment_scores(self, course_id):
        """Manual points for assignments in one course, including ungraded work."""
        return self.db.execute(
            "SELECT a.id, a.title, a.due, s.earned, s.possible "
            "FROM assignments a LEFT JOIN assignment_scores s "
            "ON s.assignment_id=a.id WHERE a.course_id=? "
            "ORDER BY a.due, a.title", (course_id,),
        ).fetchall()

    def set_assignment_score(self, assignment_id, earned, possible):
        try:
            from .study_progress import valid_score
        except ImportError:
            from study_progress import valid_score
        earned, possible = valid_score(earned, possible)
        if self.assignment_record(assignment_id) is None:
            raise ValueError("The assignment no longer exists.")
        with self.db:
            self.db.execute(
                "INSERT INTO assignment_scores(assignment_id, earned, possible) "
                "VALUES(?, ?, ?) ON CONFLICT(assignment_id) DO UPDATE SET "
                "earned=excluded.earned, possible=excluded.possible, "
                "updated_at=CURRENT_TIMESTAMP",
                (assignment_id, str(earned), str(possible)),
            )

    def clear_assignment_score(self, assignment_id):
        with self.db:
            self.db.execute(
                "DELETE FROM assignment_scores WHERE assignment_id=?",
                (assignment_id,),
            )

    def study_sessions(self, course_id):
        return self.db.execute(
            "SELECT id, topic, minutes, created_at FROM study_sessions "
            "WHERE course_id=? ORDER BY created_at DESC, id DESC LIMIT 100",
            (course_id,),
        ).fetchall()

    def add_study_session(self, course_id, topic, minutes):
        try:
            from .study_progress import valid_study_session
        except ImportError:
            from study_progress import valid_study_session
        topic, minutes = valid_study_session(topic, minutes)
        if self.course(course_id) is None:
            raise ValueError("The course no longer exists.")
        with self.db:
            return self.db.execute(
                "INSERT INTO study_sessions(course_id, topic, minutes) "
                "VALUES (?, ?, ?)", (course_id, topic, minutes),
            ).lastrowid

    def delete_study_session(self, course_id, session_id):
        with self.db:
            self.db.execute(
                "DELETE FROM study_sessions WHERE course_id=? AND id=?",
                (course_id, session_id),
            )

    def assignment_steps(self, assignment_id):
        return self.db.execute(
            "SELECT id, assignment_id, title, due, completed "
            "FROM assignment_steps WHERE assignment_id=? "
            "ORDER BY completed ASC, CASE WHEN due = '' THEN 1 ELSE 0 END, due, id",
            (assignment_id,),
        ).fetchall()

    def add_assignment_step(self, assignment_id, title, due=""):
        return self.add_assignment_steps(assignment_id, [(title, due)]) > 0

    def add_assignment_steps(self, assignment_id, items):
        try:
            from .milestones import valid_step
        except ImportError:
            from milestones import valid_step
        if self.assignment_record(assignment_id) is None:
            raise ValueError("Assignment no longer exists.")
        if len(items) > 100:
            raise ValueError("Add at most 100 steps at once.")
        checked = [(assignment_id,) + valid_step(title, due)
                   for title, due in items]
        with self.db:
            previous = self.db.total_changes
            self.db.executemany(
                "INSERT OR IGNORE INTO assignment_steps(assignment_id, title, due) "
                "VALUES (?, ?, ?)", checked)
            return self.db.total_changes - previous

    def set_step_completed(self, assignment_id, step_id, completed):
        if not isinstance(completed, bool):
            raise ValueError("Step completion must be True or False.")
        with self.db:
            return self.db.execute(
                "UPDATE assignment_steps SET completed=? "
                "WHERE assignment_id=? AND id=?",
                (int(completed), assignment_id, step_id),
            ).rowcount == 1

    def delete_assignment_step(self, assignment_id, step_id):
        with self.db:
            self.db.execute(
                "DELETE FROM assignment_steps WHERE assignment_id=? AND id=?",
                (assignment_id, step_id),
            )

    def assignment_sources(self, assignment_id):
        return self.db.execute(
            "SELECT id, assignment_id, reference, locator, notes "
            "FROM assignment_sources WHERE assignment_id=? ORDER BY id",
            (assignment_id,),
        ).fetchall()

    def assignment_source(self, assignment_id, source_id):
        return self.db.execute(
            "SELECT id, reference, locator, notes FROM assignment_sources "
            "WHERE assignment_id=? AND id=?",
            (assignment_id, source_id),
        ).fetchone()

    def add_assignment_source(self, assignment_id, reference, locator="", notes=""):
        try:
            from .milestones import valid_source
        except ImportError:
            from milestones import valid_source
        reference, locator, notes = valid_source(reference, locator, notes)
        if self.assignment_record(assignment_id) is None:
            raise ValueError("Assignment no longer exists.")
        with self.db:
            return self.db.execute(
                "INSERT OR IGNORE INTO assignment_sources "
                "(assignment_id, reference, locator, notes) VALUES (?, ?, ?, ?)",
                (assignment_id, reference, locator, notes),
            ).rowcount == 1

    def delete_assignment_source(self, assignment_id, source_id):
        with self.db:
            self.db.execute(
                "DELETE FROM assignment_sources WHERE assignment_id=? AND id=?",
                (assignment_id, source_id),
            )

    def planner_rows(self):
        """Every course, dates entered locally, with next incomplete step."""
        return self.db.execute(
            "SELECT a.id, a.course_id, c.name AS course, a.title, a.due, a.status, "
            "(SELECT COUNT(*) FROM assignment_steps s WHERE s.assignment_id=a.id) "
            "AS steps_total, "
            "(SELECT COUNT(*) FROM assignment_steps s WHERE s.assignment_id=a.id "
            "AND s.completed=1) AS steps_done, "
            "(SELECT s.title FROM assignment_steps s "
            "WHERE s.assignment_id=a.id AND s.completed=0 "
            "ORDER BY CASE WHEN s.due='' THEN 1 ELSE 0 END, s.due, s.id LIMIT 1) "
            "AS next_step "
            "FROM assignments a JOIN courses c ON c.id=a.course_id ORDER BY a.id"
        ).fetchall()

    def all_assignments(self):
        return self.db.execute(
            'SELECT a.id, a.title, a.due, a.status, c.name AS course '
            'FROM assignments a JOIN courses c ON c.id=a.course_id ORDER BY a.id'
        ).fetchall()

    def close(self):
        self.db.close()
