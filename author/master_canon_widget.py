"""The native Master Canon desk. No AI calls and no automatic canon edits."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget
)


class ClaimDialog(QDialog):
    """A proposed canon entry may only be established by manual confirmation."""

    def __init__(self, store, active_book_id=None, claim=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.previous = claim
        self.setWindowTitle('Master Canon / ' + ('Edit entry' if claim else 'New entry'))
        self.resize(680, 650)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.book = QComboBox()
        self.book.addItem('Global / all Broken World books', None)
        for b in store.books():
            self.book.addItem(b['title'], b['id'])
        self.book.currentIndexChanged.connect(self.populate_chapters)
        self.entity = QComboBox()
        self.entity.addItem('No character or entity link', None)
        for e in store.atlas.entities():
            self.entity.addItem(e['kind'] + ' / ' + e['name'], e['id'])
        self.chapter = QComboBox()
        self.category = QComboBox()
        self.category.addItems(store.master_canon.CATEGORIES)
        self.status = QComboBox()
        for key, label in (
            ('proposed', 'Proposed / awaiting approval'),
            ('established', 'Established canon'),
            ('superseded', 'Superseded / retained for history'),
        ):
            self.status.addItem(label, key)
        self.fact_key = QLineEdit()
        self.fact_key.setMaxLength(150)
        self.fact_key.setPlaceholderText('e.g. city-suffering-rule')
        self.title = QLineEdit()
        self.title.setMaxLength(200)
        self.statement = QTextEdit()
        self.statement.setAcceptRichText(False)
        self.statement.setPlaceholderText('Enter the exact fact you intend to record.')
        self.quote = QTextEdit()
        self.quote.setAcceptRichText(False)
        self.quote.setPlaceholderText('Optional verbatim excerpt from the saved chapter')
        for name, widget in (
            ('Scope', self.book), ('Linked entity', self.entity),
            ('Source chapter', self.chapter), ('Category', self.category),
            ('Status', self.status), ('Fact key', self.fact_key),
            ('Short title', self.title), ('Statement', self.statement),
            ('Source quotation', self.quote),
        ):
            form.addRow(name, widget)
        layout.addLayout(form)
        warning = QLabel(
            'New claims start as Proposed. Use Established only for canon you '
            'explicitly approve. Conflicting established facts are flagged '
            'for review, not automatically corrected. Existing source prose '
            'will never be edited.'
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        scope = claim['book_id'] if claim else active_book_id
        self.book.setCurrentIndex(max(0, self.book.findData(scope)))
        self.populate_chapters()
        if claim:
            self.entity.setCurrentIndex(max(0, self.entity.findData(claim['entity_id'])))
            self.chapter.setCurrentIndex(max(0, self.chapter.findData(claim['chapter_id'])))
            self.category.setCurrentText(claim['category'])
            self.status.setCurrentIndex(self.status.findData(claim['status']))
            self.fact_key.setText(claim['fact_key'])
            self.title.setText(claim['title'])
            self.statement.setPlainText(claim['statement'])
            self.quote.setPlainText(claim['source_quote'])

    def populate_chapters(self, *_):
        """Never leave a stale book's chapter selected after scope changes."""
        self.chapter.clear()
        self.chapter.addItem('No chapter anchor', None)
        scope = self.book.currentData()
        if scope is None:
            books = self.store.books()
        else:
            books = [b for b in self.store.books() if b['id'] == scope]
        for book in books:
            for chapter in self.store.chapters(book['id']):
                self.chapter.addItem(book['title'] + ' / ' + chapter['title'],
                                     chapter['id'])

    def values(self):
        return {
            'book_id': self.book.currentData(),
            'entity_id': self.entity.currentData(),
            'chapter_id': self.chapter.currentData(),
            'category': self.category.currentText(),
            'fact_key': self.fact_key.text(),
            'title': self.title.text(),
            'statement': self.statement.toPlainText(),
            'status': self.status.currentData(),
            'source_quote': self.quote.toPlainText(),
        }

    def accept(self):
        values = self.values()
        prior = self.previous['status'] if self.previous else 'proposed'
        if values['status'] == 'established' and prior != 'established':
            yes = QMessageBox.question(
                self, 'Confirm official canon',
                'Mark this statement as ESTABLISHED canon? '
                'This is your explicit editorial approval. '
                'Source evidence may still be absent or outdated.',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if yes != QMessageBox.Yes:
                return
        super().accept()


class MasterCanonWidget(QWidget):
    chapterRequested = pyqtSignal(int, str, str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.book_id = None
        self._rows = {}
        root = QVBoxLayout(self)
        heading = QLabel('MASTER CANON  /  Your Broken World source of truth')
        root.addWidget(heading)
        hint = QLabel(
            'Globally shared rules, character dossiers and book-specific facts. '
            'Nothing is promoted from brainstorming or AI review automatically.'
        )
        hint.setWordWrap(True)
        root.addWidget(hint)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search rules, character history, locations, clues...')
        self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search)
        self.all_books = QCheckBox('Entire library')
        self.all_books.toggled.connect(self.refresh)
        bar.addWidget(self.all_books)
        self.status_filter = QComboBox()
        for label, key in (
            ('All stages', None), ('Established', 'established'),
            ('Proposed', 'proposed'), ('Superseded', 'superseded')
        ):
            self.status_filter.addItem(label, key)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.status_filter)
        root.addLayout(bar)

        dossier = QHBoxLayout()
        dossier.addWidget(QLabel('Character / entity dossier:'))
        self.entity_filter = QComboBox()
        self.entity_filter.currentIndexChanged.connect(self.refresh)
        dossier.addWidget(self.entity_filter, 1)
        self.refresh_entities = QPushButton('Reload characters')
        self.refresh_entities.clicked.connect(self.update_entities)
        dossier.addWidget(self.refresh_entities)
        root.addLayout(dossier)

        self.summary = QLabel('No book selected.')
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            'Type','Title','Book','Character / Entity','Status','Source','Fact key'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_entry())
        root.addWidget(self.table, 2)

        actions = QHBoxLayout()
        for label, method in [
            ('Add canon proposal', self.add_entry),
            ('Edit selected', self.edit_entry),
            ('Open source chapter', self.open_source),
            ('Check canon evidence', self.audit),
            ('Read legacy canon notes', self.show_legacy_notes)
        ]:
            button = QPushButton(label)
            button.clicked.connect(method)
            actions.addWidget(button)
        root.addLayout(actions)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText('Evidence and continuity review results appear here.')
        root.addWidget(self.details, 1)
        self.update_entities()

    def set_book(self, book_id):
        self.book_id = book_id
        self.refresh()

    def update_entities(self, *_):
        saved = self.entity_filter.currentData()
        self.entity_filter.blockSignals(True)
        self.entity_filter.clear()
        self.entity_filter.addItem('All characters and entities', None)
        for entity in self.store.atlas.entities():
            self.entity_filter.addItem(
                entity['kind'] + ' / ' + entity['name'], entity['id']
            )
        self.entity_filter.setCurrentIndex(
            max(0, self.entity_filter.findData(saved))
        )
        self.entity_filter.blockSignals(False)
        self.refresh()

    def refresh(self, *_):
        self.table.setRowCount(0)
        self._rows.clear()
        try:
            rows = self.store.master_canon.claims(
                book_id=self.book_id, include_all=self.all_books.isChecked()
                or self.book_id is None,
                entity_id=self.entity_filter.currentData(),
                status=self.status_filter.currentData(),
                query=self.search.text()
            )
        except ValueError as exc:
            self.summary.setText('Canon search unavailable: ' + str(exc))
            return
        self._rows = {row['id']: row for row in rows}
        self.table.setRowCount(len(rows))
        for index, claim in enumerate(rows):
            evidence = self.store.master_canon.evidence_status(claim)
            labels = [
                claim['category'], claim['title'],
                claim['book_title'] or 'Global',
                claim['entity_name'] or '',
                claim['status'].capitalize(), evidence.replace('-', ' '),
                claim['fact_key']
            ]
            for col, label in enumerate(labels):
                item = QTableWidgetItem(label)
                item.setData(Qt.UserRole, claim['id'])
                if evidence in ('missing','outdated'):
                    item.setForeground(QBrush(QColor('#ffb4a2')))
                self.table.setItem(index, col, item)
        totals = {s:sum(r['status'] == s for r in rows)
                  for s in self.store.master_canon.STATUSES}
        self.summary.setText(
            f"{len(rows)} claims | {totals['established']} established | "
            f"{totals['proposed']} proposed | {totals['superseded']} superseded"
        )

    def _current(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return self._rows.get(selected[0].data(Qt.UserRole))

    def _edit(self, claim=None):
        dialog = ClaimDialog(self.store, active_book_id=self.book_id,
                             claim=claim, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.values()
        try:
            if claim is None:
                self.store.master_canon.add(**values)
            else:
                self.store.master_canon.edit(claim['id'], **values)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Master Canon', str(error))
            return
        self.refresh()

    def add_entry(self):
        self._edit()

    def edit_entry(self):
        claim = self._current()
        if claim is not None:
            self._edit(claim)

    def open_source(self):
        claim = self._current()
        if claim is not None and claim['chapter_id'] is not None:
            self.chapterRequested.emit(
                claim['chapter_id'], claim['source_quote'], claim['source_digest']
            )

    def show_legacy_notes(self):
        """Offer existing notebook material without promoting it to established canon."""
        scope = list(self.store.books()) if (
            self.all_books.isChecked() or self.book_id is None
        ) else [book for book in self.store.books()
                if book['id'] == self.book_id]
        lines = [
            'EXISTING AUTHOR NOTES / UNREVIEWED SOURCE MATERIAL',
            'These records remain in their original Canon notes and Story Bible.',
            'Nothing here is automatically established or migrated.',
            '',
        ]
        for book in scope:
            canon_text = self.store.canon(book['id'])
            entries = self.store.story_entries(book['id'])
            if not canon_text.strip() and not entries:
                continue
            lines.append('BOOK: ' + book['title'])
            if canon_text.strip():
                lines.append('Original canon notebook:')
                lines.append(canon_text)
            for entry in entries:
                lines.append(
                    'Story Bible / ' + entry['category'] + ' / ' + entry['title']
                )
                lines.append(entry['body'])
            lines.append('')
        if len(lines) == 4:
            lines.append('No legacy Canon notes or Story Bible entries found in this scope.')
        self.details.setPlainText('\n'.join(lines))

    def audit(self):
        report = self.store.master_canon.audit(
            book_id=self.book_id,
            include_all=self.all_books.isChecked() or self.book_id is None
        )
        lines = [
            'MASTER CANON REVIEW / HUMAN APPROVAL REQUIRED',
            f"Claims reviewed: {report['total']}",
            'Stages: ' + ', '.join(
                f"{key}: {count}" for key,count in report['statuses'].items()
            ),
            'Evidence: ' + ', '.join(
                f"{key}: {count}" for key,count in sorted(report['evidence'].items())
            ),
            f"Review flags: {len(report['alerts'])}",
            '',
        ]
        lines.extend(
            str(i) + '. ' + alert['message']
            for i,alert in enumerate(report['alerts'], 1)
        )
        if not report['alerts']:
            lines.append(
                'No issues detected among indexed claims. This does not prove '
                'unindexed manuscripts or notes are consistent.'
            )
        self.details.setPlainText('\n'.join(lines))
