"""Owner-entered source vault for a single assignment.

No automatic source verification, invented citations, or network requests.
References are appended to the assignment only after explicit selection.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QInputDialog,
)
try:
    from .milestones import valid_source
except ImportError:
    from milestones import valid_source


class AssignmentSourcesDialog(QDialog):
    def __init__(self, store, assignment_id, parent=None):
        super().__init__(parent)
        self.store = store
        self.assignment_id = assignment_id
        if store.assignment_record(assignment_id) is None:
            raise ValueError("Assignment no longer exists.")
        self.selected_reference = None
        self.setWindowTitle("Study | Research source notebook")
        self.resize(820, 520)
        layout = QVBoxLayout(self)
        heading = QLabel(
            "Enter complete references yourself. This list does not verify "
            "an author, journal, DOI, URL, or APA formatting.")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        actions = QHBoxLayout()
        for title, function in [
            ("Add source", self.add_source),
            ("View details", self.details),
            ("Use in References", self.use_selected),
            ("Delete selected", self.delete_selected),
        ]:
            button = QPushButton(title)
            button.clicked.connect(function)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for source in self.store.assignment_sources(self.assignment_id):
            item = QListWidgetItem(source["reference"][:190])
            item.setData(Qt.UserRole, source["id"])
            self.list.addItem(item)

    def selected(self):
        item = self.list.currentItem()
        return (self.store.assignment_source(self.assignment_id, item.data(Qt.UserRole))
                if item else None)

    def add_source(self):
        ref, ok = QInputDialog.getMultiLineText(
            self, "Owner-entered reference", "Full source reference (unverified):")
        if not ok:
            return
        locator, ok = QInputDialog.getText(
            self, "Source locator", "Optional URL, DOI, ISBN, or library location:")
        if not ok:
            return
        notes, ok = QInputDialog.getMultiLineText(
            self, "Research notes", "Optional notes about how you used this source:")
        if not ok:
            return
        try:
            ref, locator, notes = valid_source(ref, locator, notes)
            if not self.store.add_assignment_source(
                    self.assignment_id, ref, locator, notes):
                QMessageBox.information(self, "Source notebook", "Reference already saved.")
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Source notebook", str(error))

    def details(self):
        row = self.selected()
        if not row:
            return
        QMessageBox.information(
            self, "Owner-entered source (unverified)",
            row["reference"] + "\n\nLocator:\n" + (row["locator"] or "(none)") +
            "\n\nNotes:\n" + (row["notes"] or "(none)") +
            "\n\nVerify publication metadata, links, and APA formatting yourself.")

    def use_selected(self):
        row = self.selected()
        if not row:
            return
        if QMessageBox.question(
                self, "Use reference",
                "Append this source exactly as entered to your assignment's "
                "References section? This does not verify the citation.") == QMessageBox.Yes:
            self.selected_reference = row["reference"]
            self.accept()

    def delete_selected(self):
        row = self.selected()
        if not row:
            return
        if QMessageBox.question(
                self, "Delete source", "Delete this saved source note? "
                "Existing text already copied into References stays unchanged."
        ) == QMessageBox.Yes:
            self.store.delete_assignment_source(self.assignment_id, row["id"])
            self.refresh()
