"""Owner-controlled reading library and preview picker for Study."""
from pathlib import Path
try:
    from .reading_passages import search_reading_passages, selected_passage_text
except ImportError:
    from reading_passages import search_reading_passages, selected_passage_text
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox,
    QFileDialog, QTextEdit,
)
try:
    from .reading_library import (
        import_course_reading, find_course_excerpts, selected_reading_excerpt,
        reindex_course_reading)
except ImportError:
    from reading_library import (
        import_course_reading, find_course_excerpts, selected_reading_excerpt)


class ReadingLibraryDialog(QDialog):
    def __init__(self, store, course_id, parent=None, *, pick=False):
        super().__init__(parent)
        self.store = store
        self.course_id = course_id
        self.pick = pick
        self.selected_excerpt = None
        self._showing_passages = False
        course = self.store.course(course_id)
        if course is None:
            raise ValueError("Choose a valid existing Study course.")
        self.setWindowTitle("Study | " + course["name"] + " | Reading Library")
        self.resize(950, 740)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Import only readings you select. Study makes a NEW private copy in "
            "the course Readings folder and indexes up to 240,000 text characters " 
            "as locally searchable numbered passages. "
            "Sources are never automatically sent to Webbie, verified, or cited.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        search_bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search indexed text, e.g. emotional regulation")
        self.search.returnPressed.connect(self.search_readings)
        search_bar.addWidget(self.search, 1)
        search_btn = QPushButton("Search this course")
        search_btn.clicked.connect(self.search_readings)
        search_bar.addWidget(search_btn)
        layout.addLayout(search_bar)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Reading", "Match / location"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.preview_selected)
        layout.addWidget(self.table, 1)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(230)
        self.preview.setPlaceholderText("Select a reading to preview the saved text.")
        layout.addWidget(self.preview)
        actions = QHBoxLayout()
        for caption, callback in [
            ("Import chosen file", self.import_file),
            ("Show all readings", self.show_all),
            ("Browse passages", self.browse_passages),
            ("Expand older index", self.reindex_selected),
            ("Open copied file", self.open_file),
            ("Use selected passage", self.use_selected),
        ]:
            button = QPushButton(caption)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel("Ready. No document has been transferred.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        close = QPushButton("Close Reading Library")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        self.show_all()

    def _populate(self, rows, snippets=None):
        self._showing_passages = False
        snippets = snippets or {}
        self.table.setRowCount(0)
        for record in rows:
            index = self.table.rowCount()
            self.table.insertRow(index)
            title = QTableWidgetItem(record["title"])
            title.setData(Qt.UserRole, record["id"])
            self.table.setItem(index, 0, title)
            text = snippets.get(record["id"], record.get("relative_path", ""))
            self.table.setItem(index, 1, QTableWidgetItem(text[:400]))
        self.preview.clear()

    def _populate_passages(self, rows):
        self._showing_passages = True
        self.table.setRowCount(0)
        for hit in rows:
            index = self.table.rowCount()
            self.table.insertRow(index)
            title = QTableWidgetItem(hit["title"])
            title.setData(Qt.UserRole, (hit["id"], hit["passage_index"]))
            self.table.setItem(index, 0, title)
            label = (f"Passage {hit['passage_index']} "
                     f"(extracted chars {hit['start_char']}-{hit['end_char']}): "
                     + str(hit["snippet"])[:300])
            self.table.setItem(index, 1, QTableWidgetItem(label))
        self.preview.clear()

    def show_all(self):
        rows = [dict(row) for row in self.store.course_readings(self.course_id)]
        self._populate(rows)
        self.status.setText(f"{len(rows)} manually indexed readings in this course.")

    def search_readings(self):
        query = self.search.text().strip()
        if not query:
            self.show_all()
            return
        try:
            matches = search_reading_passages(
                self.store.reading_passage_candidates(self.course_id), query)
            indexed_ids = {x["reading_id"] for x in
                           self.store.reading_passage_candidates(self.course_id)}
            older = [r for r in self.store.course_readings(self.course_id)
                     if r["id"] not in indexed_ids]
            legacy = find_course_excerpts(older, query) if older else []
        except ValueError as error:
            QMessageBox.warning(self, "Reading search", str(error))
            return
        if matches:
            self._populate_passages(matches)
            self.status.setText(
                f"{len(matches)} passage results; no Webbie request made. "
                "Older 12K-only readings can be expanded with Expand older index.")
        else:
            records = [dict(self.store.course_reading(self.course_id, row["id"]))
                       for row in legacy]
            self._populate(records, {row["id"]: row["snippet"] for row in legacy})
            self.status.setText(
                f"{len(legacy)} legacy reading matches. "
                "Use Expand older index to search beyond their initial excerpts.")

    def selected_record(self):
        index = self.table.currentRow()
        item = self.table.item(index, 0) if index >= 0 else None
        if item is None:
            return None
        key = item.data(Qt.UserRole)
        reading_id = key[0] if isinstance(key, tuple) else key
        return self.store.course_reading(self.course_id, reading_id)

    def selected_passage(self):
        if not self._showing_passages:
            return None
        item = self.table.item(self.table.currentRow(), 0) if self.table.currentRow() >= 0 else None
        key = item.data(Qt.UserRole) if item else None
        if not isinstance(key, tuple) or len(key) != 2:
            return None
        return self.store.reading_passage(self.course_id, key[0], key[1])

    def preview_selected(self):
        record = self.selected_record()
        if record:
            passage = self.selected_passage()
            if passage:
                self.preview.setPlainText(selected_passage_text(record, passage))
            else:
                count = len(self.store.reading_passages(self.course_id, record["id"]))
                self.preview.setPlainText(
                    "READING: " + record["title"] +
                    f"\nIndexed passages: {count if count else 'Legacy 12K excerpt'}" +
                    "\n\n" + record["excerpt"] +
                    "\n\nThis opening excerpt is not the entire document. "
                    "Use Browse passages or search for passages later in the reading.")
        else:
            self.preview.clear()

    def import_file(self):
        folder = self.store.course_folder(self.course_id)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a course reading to copy into Study", str(folder),
            "Readable documents (*.txt *.md *.docx *.pdf)")
        if not path:
            return
        if QMessageBox.question(
                self, "Confirm local reading import",
                "Make a NEW copy of " + Path(path).name +
                " inside this course and index the extractable text? "
                "The original file is never removed.") != QMessageBox.Yes:
            return
        try:
            result = import_course_reading(self.store, self.course_id, path)
            self.show_all()
            if result["created"]:
                self.status.setText("Reading copied and indexed privately: " +
                                    result["location"])
            else:
                self.status.setText("Skipped identical reading: " + result["name"])
        except (ValueError, OSError, RuntimeError, ImportError,
                UnicodeError, TimeoutError) as error:
            QMessageBox.warning(self, "Reading import", str(error))

    def browse_passages(self):
        """Owner chooses which stored passage to read or send to Webbie."""
        record = self.selected_record()
        if record is None:
            QMessageBox.information(self, "Reading passages", "Select a reading first.")
            return
        rows = self.store.reading_passages(self.course_id, record["id"])
        if not rows:
            QMessageBox.information(
                self, "Older reading", "Only the first 12K characters are indexed. "
                "Select Expand older index to index the full bounded text.")
            return
        results = [{
            "id": record["id"], "title": record["title"],
            "passage_index": row["passage_index"],
            "start_char": row["start_char"], "end_char": row["end_char"],
            "snippet": row["body"][:300]
        } for row in rows]
        self._populate_passages(results)
        self.status.setText(f"Showing {len(results)} passages. Select one to preview.")

    def reindex_selected(self):
        """Explicit opt-in reindex, never crawl course folders or overwrite content."""
        record = self.selected_record()
        if record is None:
            QMessageBox.information(self, "Reading index", "Select a reading first.")
            return
        if self.store.reading_passages(self.course_id, record["id"]):
            self.status.setText("This reading already has a passage index.")
            return
        if QMessageBox.question(
                self, "Expand older reading index",
                "Index more text from this previously imported local reading? "
                "Only this chosen, unchanged document is read. No AI is called.") != QMessageBox.Yes:
            return
        try:
            result = reindex_course_reading(self.store, self.course_id, record["id"])
            self.status.setText(
                f"Indexed {result.get('passages', 0)} passages. "
                "Choose Browse passages or search to inspect them.")
        except (OSError, ValueError, RuntimeError, TimeoutError) as error:
            QMessageBox.warning(self, "Reading reindex", str(error))

    def open_file(self):
        record = self.selected_record()
        if record is None:
            return
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        root = self.store.course_folder(self.course_id)
        path = root / record["relative_path"]
        if (path.is_symlink() or not path.is_file() or
                not path.resolve().is_relative_to(root.resolve())):
            QMessageBox.warning(self, "Open reading", "Copied reading no longer exists.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def use_selected(self):
        record = self.selected_record()
        if record is None:
            QMessageBox.information(self, "Select reading", "Select a reading first.")
            return
        if not self.pick:
            QMessageBox.information(
                self, "Use in Webbie",
                "Open Study Coach or Webbie Homework to select this reading. "
                "No material was sent.")
            return
        passage = self.selected_passage()
        excerpt = (selected_passage_text(record, passage) if passage else
                   selected_reading_excerpt(record))
        if QMessageBox.question(
                self, "Use selected reading",
                "Copy this reading excerpt into the assistant's editable materials "
                "field for your review? Webbie will NOT run automatically."
        ) != QMessageBox.Yes:
            return
        self.selected_excerpt = excerpt
        self.accept()
