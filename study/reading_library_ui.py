"""Owner-controlled reading library and preview picker for Study."""
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox,
    QFileDialog, QTextEdit,
)
try:
    from .reading_library import (
        import_course_reading, find_course_excerpts, selected_reading_excerpt)
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
        course = self.store.course(course_id)
        if course is None:
            raise ValueError("Choose a valid existing Study course.")
        self.setWindowTitle("Study | " + course["name"] + " | Reading Library")
        self.resize(950, 740)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Import only readings you select. Study makes a NEW private copy in "
            "the course Readings folder and indexes up to 12,000 text characters. "
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
            ("Open copied file", self.open_file),
            ("Use selected excerpt", self.use_selected),
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
            matched = find_course_excerpts(
                self.store.course_readings(self.course_id), query)
        except ValueError as error:
            QMessageBox.warning(self, "Reading search", str(error))
            return
        records = [dict(self.store.course_reading(self.course_id, row["id"]))
                   for row in matched]
        self._populate(records, {row["id"]: row["snippet"] for row in matched})
        self.status.setText(f"{len(matched)} matching readings. No Webbie request made.")

    def selected_record(self):
        index = self.table.currentRow()
        item = self.table.item(index, 0) if index >= 0 else None
        if item is None:
            return None
        return self.store.course_reading(self.course_id, item.data(Qt.UserRole))

    def preview_selected(self):
        record = self.selected_record()
        if record:
            self.preview.setPlainText(
                "READING: " + record["title"] + "\n\n" + record["excerpt"] +
                "\n\nOnly the indexed first 12,000 characters are shown.")
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
        excerpt = selected_reading_excerpt(record)
        if QMessageBox.question(
                self, "Use selected reading",
                "Copy this reading excerpt into the assistant's editable materials "
                "field for your review? Webbie will NOT run automatically."
        ) != QMessageBox.Yes:
            return
        self.selected_excerpt = excerpt
        self.accept()
