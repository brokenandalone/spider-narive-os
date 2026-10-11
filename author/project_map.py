"""Native private Author chapter map and editorial progress controls.

The Project Map only edits chapter *metadata*. Manuscript contents and canon
remain authoritative in AuthorStore and are never rewritten here.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)


class ProjectMap(QWidget):
    chapterRequested = pyqtSignal(int)
    statusChanged = pyqtSignal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.book_id = None
        self.selected_id = None
        self.rows = []
        self.dirty = False
        self._loading = False

        layout = QVBoxLayout(self)
        title = QLabel('PROJECT MAP  /  Chapters, revision progress and scene notes')
        layout.addWidget(title)
        self.summary = QLabel('Select a book to see your manuscript outline.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        bar = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText('Filter chapters by title, status, or private notes')
        self.query.textChanged.connect(self.render_list)
        bar.addWidget(self.query)
        refresh = QPushButton('Refresh chapter map')
        refresh.clicked.connect(self.refresh)
        bar.addWidget(refresh)
        layout.addLayout(bar)

        body = QHBoxLayout()
        layout.addLayout(body, 1)
        self.chapter_list = QListWidget()
        self.chapter_list.currentItemChanged.connect(self.select_row)
        self.chapter_list.itemActivated.connect(lambda *_: self.open_chapter())
        body.addWidget(self.chapter_list, 2)

        self.detail = QWidget()
        fields = QVBoxLayout(self.detail)
        self.chapter_name = QLabel('Choose a chapter.')
        self.chapter_name.setWordWrap(True)
        fields.addWidget(self.chapter_name)
        self.counts = QLabel('')
        fields.addWidget(self.counts)
        fields.addWidget(QLabel('Editorial stage'))
        self.stage = QComboBox()
        for value, label in (
            ('draft', 'Draft'), ('revising', 'In revision'), ('ready', 'Ready')
        ):
            self.stage.addItem(label, value)
        self.stage.currentIndexChanged.connect(self.mark_dirty)
        fields.addWidget(self.stage)
        fields.addWidget(QLabel('Target word count (0 means no target)'))
        self.target = QSpinBox()
        self.target.setRange(0, 200000)
        self.target.valueChanged.connect(self.mark_dirty)
        fields.addWidget(self.target)
        fields.addWidget(QLabel('Private chapter / scene notes'))
        self.notes = QTextEdit()
        self.notes.setAcceptRichText(False)
        self.notes.setPlaceholderText(
            'Scene purpose, character motivations, foreshadowing, timeline...'
        )
        self.notes.textChanged.connect(self.mark_dirty)
        fields.addWidget(self.notes, 1)
        actions = QHBoxLayout()
        self.save_button = QPushButton('Save chapter plan')
        self.save_button.clicked.connect(self.save_and_refresh)
        self.save_button.setEnabled(False)
        actions.addWidget(self.save_button)
        open_button = QPushButton('Open chapter in editor')
        open_button.clicked.connect(self.open_chapter)
        actions.addWidget(open_button)
        fields.addLayout(actions)
        self.detail.setEnabled(False)
        body.addWidget(self.detail, 3)

    def set_book(self, book_id):
        if not self.save_pending():
            return False
        self.book_id = book_id
        self.selected_id = None
        self.query.blockSignals(True)
        self.query.clear()
        self.query.blockSignals(False)
        return self.refresh()

    def refresh(self, *_):
        """Refresh statistics from saved manuscript text; do not trigger AI."""
        if not self.save_pending():
            return False
        self.rows = self.store.project_outline(self.book_id) if self.book_id is not None else []
        total = sum(r['words'] for r in self.rows)
        targets = sum(r['target_words'] for r in self.rows)
        ready = sum(r['status'] == 'ready' for r in self.rows)
        revising = sum(r['status'] == 'revising' for r in self.rows)
        count = len(self.rows)
        if self.book_id is None:
            self.summary.setText('Select a book to see your manuscript outline.')
        else:
            goal = f' | {targets:,} target words' if targets else ''
            self.summary.setText(
                f'{count} chapters | {total:,} words | '
                f'{ready} ready | {revising} in revision{goal}'
            )
        self.render_list()
        return True

    def _label(self, chapter, number):
        goal = (' / ' + format(chapter['target_words'], ',') + ' goal'
                if chapter['target_words'] else '')
        stage = {'draft':'Draft', 'revising':'Revising', 'ready':'Ready'}[
            chapter['status']
        ]
        return (
            f"{number:02d}   {chapter['title']}   "
            f"[{stage} | {chapter['words']:,} words{goal}]"
        )

    def render_list(self, *_):
        if not self.save_pending():
            return
        query = self.query.text().strip().casefold()
        keep = self.selected_id
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        selected_item = None
        for number, row in enumerate(self.rows, 1):
            if query and query not in (
                row['title'] + ' ' + row['status'] + ' ' + row['notes']
            ).casefold():
                continue
            item = QListWidgetItem(self._label(row, number))
            item.setData(Qt.UserRole, row['id'])
            self.chapter_list.addItem(item)
            if row['id'] == keep:
                selected_item = item
        if selected_item is None and self.chapter_list.count():
            selected_item = self.chapter_list.item(0)
        self.chapter_list.setCurrentItem(selected_item)
        self.chapter_list.blockSignals(False)
        self._load_item(selected_item)

    def select_row(self, item, previous=None):
        old = self.selected_id
        if not self.save_pending():
            self.chapter_list.blockSignals(True)
            for index in range(self.chapter_list.count()):
                candidate = self.chapter_list.item(index)
                if candidate.data(Qt.UserRole) == old:
                    self.chapter_list.setCurrentItem(candidate)
                    break
            self.chapter_list.blockSignals(False)
            return
        self._load_item(item)

    def _load_item(self, item):
        ident = item.data(Qt.UserRole) if item else None
        self.selected_id = ident
        self.detail.setEnabled(ident is not None)
        self._loading = True
        try:
            row = next((r for r in self.rows if r['id'] == ident), None)
            if row is None:
                self.chapter_name.setText('Choose a chapter.')
                self.counts.clear()
                self.stage.setCurrentIndex(0)
                self.target.setValue(0)
                self.notes.clear()
            else:
                self.chapter_name.setText(row['title'])
                self.counts.setText(f"{row['words']:,} words in saved manuscript")
                self.stage.setCurrentIndex(self.stage.findData(row['status']))
                self.target.setValue(row['target_words'])
                self.notes.setPlainText(row['notes'])
            self.dirty = False
            self.save_button.setEnabled(False)
        finally:
            self._loading = False

    def mark_dirty(self, *_):
        if not self._loading and self.selected_id is not None:
            self.dirty = True
            self.save_button.setEnabled(True)

    def save_pending(self):
        """Called by the parent autosave and before every chapter switch."""
        if not self.dirty or self.selected_id is None:
            return True
        try:
            status = self.stage.currentData()
            target = self.target.value()
            notes = self.notes.toPlainText()
            self.store.save_chapter_plan(
                self.selected_id, status=status,
                target_words=target, notes=notes
            )
        except (OSError, ValueError, Exception) as exc:
            # Never claim saving succeeded. Do not clear pending edits.
            self.statusChanged.emit('Chapter plan save failed: ' + str(exc))
            return False
        for row in self.rows:
            if row['id'] == self.selected_id:
                row.update(
                    status=status, target_words=target, notes=notes
                )
                break
        self.dirty = False
        self.save_button.setEnabled(False)
        self.statusChanged.emit('Chapter plan saved locally.')
        return True

    def save_and_refresh(self):
        if self.save_pending():
            self.refresh()

    def open_chapter(self):
        if self.selected_id is not None and self.save_pending():
            self.chapterRequested.emit(self.selected_id)
