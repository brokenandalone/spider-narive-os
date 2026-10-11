"""Native Spider Author Story Atlas: timeline, character links and canon checks.

All operations run locally. Adding/editing story facts requires direct writer
interaction, and selecting a possible inconsistency never changes manuscript.
"""
import math
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGraphicsScene,
    QGraphicsView, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QInputDialog
)


class EventDialog(QDialog):
    """Writer-supplied chronology and exact source quote, never AI invention."""
    def __init__(self, chapters, event=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Story Atlas / Event')
        self.resize(600, 500)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(200)
        self.order_edit = QSpinBox()
        self.order_edit.setRange(-1000000, 1000000)
        self.chapter_edit = QComboBox()
        self.chapter_edit.addItem('No source chapter', None)
        for chapter in chapters:
            self.chapter_edit.addItem(chapter['title'], chapter['id'])
        self.key_edit = QLineEdit()
        self.key_edit.setMaxLength(120)
        self.key_edit.setPlaceholderText('Optional shared event key, e.g. 313-receipt')
        self.when_edit = QLineEdit()
        self.when_edit.setMaxLength(120)
        self.when_edit.setPlaceholderText('Story time, e.g. Night 1, 3:13 AM')
        self.details_edit = QTextEdit()
        self.details_edit.setAcceptRichText(False)
        self.quote_edit = QTextEdit()
        self.quote_edit.setAcceptRichText(False)
        self.quote_edit.setPlaceholderText('Exact text from the selected saved chapter')
        for label, widget in [
            ('Event title', self.title_edit),
            ('Story-order number', self.order_edit),
            ('Source chapter', self.chapter_edit),
            ('Shared continuity key', self.key_edit),
            ('When', self.when_edit),
            ('What happens / notes', self.details_edit),
            ('Exact manuscript quote (optional)', self.quote_edit),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        hint = QLabel('Shared keys are checked across books. Different time labels are flagged for writer review, never silently corrected.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if event:
            self.title_edit.setText(event['title'])
            self.order_edit.setValue(event['story_order'])
            self.chapter_edit.setCurrentIndex(
                max(0, self.chapter_edit.findData(event['chapter_id']))
            )
            self.key_edit.setText(event['event_key'])
            self.when_edit.setText(event['when_label'])
            self.details_edit.setPlainText(event['details'])
            self.quote_edit.setPlainText(event['evidence_quote'])

    def values(self):
        return {
            'title': self.title_edit.text(),
            'chapter_id': self.chapter_edit.currentData(),
            'story_order': self.order_edit.value(),
            'event_key': self.key_edit.text(),
            'when_label': self.when_edit.text(),
            'details': self.details_edit.toPlainText(),
            'evidence_quote': self.quote_edit.toPlainText(),
        }


class AtlasWidget(QWidget):
    chapterRequested = pyqtSignal(int)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.book_id = None
        self._events = {}
        root = QVBoxLayout(self)
        header = QLabel('STORY ATLAS  /  Timeline, relationships and verified story evidence')
        header.setWordWrap(True)
        root.addWidget(header)
        self.heading = QLabel('Select a book.')
        root.addWidget(self.heading)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_timeline()
        self._build_relationships()
        self._build_audit()

    def _build_timeline(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        for title, callback in [
            ('Add event', self.add_event),
            ('Edit selected', self.edit_event),
            ('Open source chapter', self.open_source),
            ('Refresh', self.refresh),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.event_table = QTableWidget(0, 6)
        self.event_table.setHorizontalHeaderLabels(
            ['Order', 'When', 'Event', 'Book', 'Chapter', 'Evidence']
        )
        self.event_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.event_table.setSelectionMode(QTableWidget.SingleSelection)
        self.event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.event_table.cellDoubleClicked.connect(lambda *_: self.open_source())
        layout.addWidget(self.event_table, 1)
        self.tabs.addTab(page, 'Timeline')

    def _build_relationships(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        for title, callback in [
            ('Add character / entity', self.add_entity),
            ('Connect two entries', self.add_relationship),
            ('Refresh graph', self.refresh),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.graph_view = QGraphicsView()
        self.graph_view.setMinimumHeight(280)
        self.graph_scene = QGraphicsScene(self.graph_view)
        self.graph_view.setScene(self.graph_scene)
        layout.addWidget(self.graph_view, 3)
        self.link_list = QListWidget()
        layout.addWidget(self.link_list, 1)
        self.tabs.addTab(page, 'Character Network')

    def _build_audit(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        explanation = QLabel(
            'This audit checks your manually tagged timeline facts and exact '
            'chapter quotes. Warnings are suggestions to inspect, not proof '
            'the story is wrong. It never edits prose or establishes canon.'
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        bar = QHBoxLayout()
        for name, all_books in [
            ('Check this book', False), ('Check entire Broken World library', True)
        ]:
            button = QPushButton(name)
            button.clicked.connect(
                lambda checked=False, all_books=all_books: self.audit(all_books)
            )
            bar.addWidget(button)
        layout.addLayout(bar)
        self.audit_result = QTextEdit()
        self.audit_result.setReadOnly(True)
        layout.addWidget(self.audit_result, 1)
        self.tabs.addTab(page, 'Continuity Checks')

    def set_book(self, book_id):
        self.book_id = book_id
        self.refresh()

    def refresh(self, *_):
        self._events = {}
        self.event_table.setRowCount(0)
        self.link_list.clear()
        self.graph_scene.clear()
        if self.book_id is None:
            self.heading.setText('Select a book to access its Story Atlas.')
            return
        book = next(
            (b for b in self.store.books() if b['id'] == self.book_id), None
        )
        if book is None:
            self.heading.setText('Book no longer available.')
            return
        self.heading.setText('Story Atlas | ' + book['title'])
        events = self.store.atlas.events(self.book_id)
        self._events = {e['id']: e for e in events}
        self.event_table.setRowCount(len(events))
        for row, event in enumerate(events):
            status = self.store.atlas.evidence_status(event)
            labels = (
                str(event['story_order']), event['when_label'], event['title'],
                event['book_title'], event['chapter_title'] or '',
                status.replace('-', ' '),
            )
            for col, text in enumerate(labels):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, event['id'])
                if status in ('outdated', 'missing'):
                    item.setForeground(QBrush(QColor('#ffb4a2')))
                self.event_table.setItem(row, col, item)
        self._render_graph()

    def _selected_event(self):
        selection = self.event_table.selectedItems()
        if not selection:
            return None
        return self._events.get(selection[0].data(Qt.UserRole))

    def _save_event(self, previous=None):
        if self.book_id is None:
            return
        dialog = EventDialog(self.store.chapters(self.book_id), previous, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            values = dialog.values()
            self.store.atlas.upsert_event(
                self.book_id, event_id=previous['id'] if previous else None,
                **values
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Story Atlas', str(exc))
            return
        self.refresh()

    def add_event(self):
        self._save_event()

    def edit_event(self):
        event = self._selected_event()
        if event is not None:
            self._save_event(event)

    def open_source(self):
        event = self._selected_event()
        if event is not None and event['chapter_id'] is not None:
            self.chapterRequested.emit(event['chapter_id'])

    def add_entity(self):
        if self.book_id is None:
            return
        name, ok = QInputDialog.getText(self, 'Atlas entry', 'Character, place, or entity name:')
        if not ok or not name.strip():
            return
        kind, ok = QInputDialog.getItem(
            self, 'Atlas category', 'Type:',
            list(self.store.atlas.ENTITY_KINDS), 0, False
        )
        if not ok:
            return
        try:
            self.store.atlas.add_entity(name, kind=kind)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Story Atlas', str(exc))
        self.refresh()

    def add_relationship(self):
        if self.book_id is None:
            return
        entities = self.store.atlas.entities()
        if len(entities) < 2:
            QMessageBox.information(
                self, 'Story Atlas', 'Add at least two entities first.'
            )
            return
        choices = [e['name'] for e in entities]
        source, ok = QInputDialog.getItem(
            self, 'Relationship source', 'From:', choices, 0, False
        )
        if not ok:
            return
        target, ok = QInputDialog.getItem(
            self, 'Relationship target', 'To:', choices, 1, False
        )
        if not ok:
            return
        relation, ok = QInputDialog.getText(
            self, 'Relationship', 'Connection, e.g. protects, distrusts, hunts:'
        )
        if not ok:
            return
        lookup = {e['name']: e['id'] for e in entities}
        try:
            self.store.atlas.add_relationship(
                self.book_id, lookup[source], lookup[target], relation
            )
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Story Atlas', str(exc))
        self.refresh()

    def _render_graph(self):
        self.graph_scene.clear()
        links = self.store.atlas.relationships(self.book_id)
        self.link_list.clear()
        for edge in links:
            self.link_list.addItem(
                f"{edge['source_name']}  →  {edge['relation']}  →  {edge['target_name']}"
            )
        by_id = {e['id']: e for e in self.store.atlas.entities()}
        used = sorted(
            {id_ for link in links
             for id_ in (link['source_entity'], link['target_entity'])},
            key=lambda id_: by_id[id_]['name'].casefold()
        )
        if not used:
            self.graph_scene.addText(
                'Connect two characters or entities to visualize their relationship.'
            ).setDefaultTextColor(QColor('#d7c7ff'))
            return
        width, height = 760, 450
        cx, cy = width / 2, height / 2
        radius = min(290, max(120, 30 * len(used)))
        positions = {}
        for index, ident in enumerate(used):
            angle = 2 * math.pi * index / len(used) - math.pi / 2
            positions[ident] = (
                cx + radius * math.cos(angle),
                cy + radius * math.sin(angle)
            )
        for edge in links:
            sx, sy = positions[edge['source_entity']]
            tx, ty = positions[edge['target_entity']]
            line = self.graph_scene.addLine(
                sx, sy, tx, ty, QPen(QColor('#8d68e8'), 2)
            )
            line.setToolTip(edge['relation'] + ': ' + edge['notes'])
            label = self.graph_scene.addText(edge['relation'][:25])
            label.setDefaultTextColor(QColor('#d0a7ff'))
            label.setPos((sx + tx) / 2, (sy + ty) / 2)
        for ident in used:
            entry = by_id[ident]
            x, y = positions[ident]
            shape = self.graph_scene.addEllipse(
                x - 31, y - 31, 62, 62, QPen(QColor('#eee0ff'), 2),
                QBrush(QColor('#562699' if entry['kind'] == 'Character' else '#7a244a'))
            )
            shape.setToolTip(entry['kind'] + ' / ' + entry['name'])
            label = self.graph_scene.addText(entry['name'][:36])
            label.setDefaultTextColor(QColor('#f7ebff'))
            label.setPos(x - 54, y + 32)
        self.graph_scene.setSceneRect(0, 0, width, height)
        self.graph_view.fitInView(self.graph_scene.sceneRect(), Qt.KeepAspectRatio)

    def audit(self, include_all=False):
        if self.book_id is None and not include_all:
            return
        try:
            report = self.store.atlas.continuity_audit(
                None if include_all else self.book_id
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Story Atlas', str(exc))
            return
        lines = [
            'STORY ATLAS / CONSERVATIVE CONTINUITY AUDIT',
            'Scope: all books' if include_all else 'Scope: selected book',
            f"Tagged events examined: {report['events']}",
            f"Exact source quotes verified: {report['verified']}",
            f"Events without exact source evidence: {report['unanchored']}",
            f"Review alerts: {len(report['alerts'])}",
            '',
        ]
        for count, alert in enumerate(report['alerts'], 1):
            lines.append(f"{count}. {alert['message']}")
        if not report['alerts']:
            lines.append(
                'No mismatches found among entered evidence. This does NOT '
                'prove untagged chapters or the manuscript are consistent.'
            )
        self.audit_result.setPlainText('\n'.join(lines))
        self.tabs.setCurrentIndex(2)
