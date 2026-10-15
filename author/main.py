#!/usr/bin/env python3
"""Native Author library, chapter editor, autosave, snapshots and canon notebook."""
import hashlib
import sys
from pathlib import Path
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QInputDialog,
    QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget)
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))
from workspace_max_native import NativeWorkspaceTools
if __package__:
    from .store import AuthorStore
    from .web_features import AuthorToolkit
    from .control_socket import AuthorCommandServer
    from .project_map import ProjectMap
    from .atlas_widget import AtlasWidget
    from .master_canon_widget import MasterCanonWidget
    from .canon_intelligence_widget import CanonIntelligenceWidget
else:
    from store import AuthorStore
    from web_features import AuthorToolkit
    from control_socket import AuthorCommandServer
    from project_map import ProjectMap
    from atlas_widget import AtlasWidget
    from master_canon_widget import MasterCanonWidget
    from canon_intelligence_widget import CanonIntelligenceWidget


class AuthorWindow(QMainWindow):
    def __init__(self, root=None):
        super().__init__()
        self.store = AuthorStore(root)
        self.book_id = self.chapter_id = None
        self.setWindowTitle('Author | Spider OS')
        # Keep owner-reviewed bounds for KDE on smaller available screens.
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        self.resize(min(1200, available.width()) if available else 1200,
                    min(800, available.height()) if available else 800)
        self.setStyleSheet('QWidget { background:#100b18; color:#eee6ff; } '
            'QTextEdit,QListWidget { background:#1b1228; } '
            'QPushButton { background:#4c1d95; padding:8px; border-radius:5px; }')
        root_widget = QWidget(); self.setCentralWidget(root_widget)
        layout = QVBoxLayout(root_widget)
        bar = QVBoxLayout(); layout.addLayout(bar)
        action_rows = (QHBoxLayout(), QHBoxLayout())
        for row in action_rows:
            bar.addLayout(row)
        for index, (label, action) in enumerate([
                ('New book', self.new_book), ('New chapter', self.new_chapter),
                ('Import text', self.import_text), ('Import DOCX', self.import_docx),
                ('Import library', self.import_bundle), ('Save', self.flush),
                ('Restore snapshot', self.restore), ('Backup library', self.backup),
                ('Focus', self.toggle_focus)]):
            button = QPushButton(label); button.clicked.connect(action)
            button.setMinimumHeight(36)
            action_rows[index // 5].addWidget(button)
            if label == 'Focus': self.focus_button = button
        split = QSplitter(); self.split = split; layout.addWidget(split)
        self.books = QListWidget(); self.books.setMinimumWidth(125); split.addWidget(self.books)
        self.chapters = QListWidget(); self.chapters.setMinimumWidth(125); split.addWidget(self.chapters)
        tabs = QTabWidget(); self.editor_tabs = tabs; tabs.setMinimumWidth(380); split.addWidget(tabs)
        split.setChildrenCollapsible(False)
        split.setSizes([170, 170, 650])
        self.editor = QTextEdit(); self.editor.setAcceptRichText(False)
        self.canon = QTextEdit(); self.canon.setAcceptRichText(False)
        tabs.addTab(self.editor, 'Chapter'); tabs.addTab(self.canon, 'Canon notes')
        self.toolkit = AuthorToolkit(self.store, self.current_chapter, self.flush, self.editor)
        self.toolkit.jumpRequested.connect(self.jump_to_search_result)
        self.toolkit.reviewSegmentRequested.connect(self.jump_to_review_segment)
        self.toolkit.reviewRequested.connect(self.author_review_requested)
        self.toolkit.editRequested.connect(self.apply_revised_passage)
        tabs.addTab(self.toolkit, 'Writing Studio')
        self.native_max_tools = NativeWorkspaceTools('author', self)
        tabs.addTab(self.native_max_tools, 'Atlas, canon & analysis')
        self.project_map = ProjectMap(self.store)
        self.project_map.chapterRequested.connect(self.jump_to_chapter_id)
        self.project_map.statusChanged.connect(self.project_map_status)
        tabs.addTab(self.project_map, 'Project Map')
        self.atlas_widget = AtlasWidget(self.store)
        self.atlas_widget.chapterRequested.connect(self.jump_to_chapter_id)
        tabs.addTab(self.atlas_widget, 'Story Atlas')
        self.master_canon_widget = MasterCanonWidget(self.store)
        self.master_canon_widget.chapterRequested.connect(self.jump_to_canon_source)
        tabs.addTab(self.master_canon_widget, 'Master Canon')
        self.canon_intelligence = CanonIntelligenceWidget(
            self.store, self.current_chapter, self.flush)
        self.canon_intelligence.sourceRequested.connect(self.jump_to_canon_source)
        tabs.addTab(self.canon_intelligence, 'Canon Intelligence')
        tabs.currentChanged.connect(self.on_tab_changed)
        self.editor.setEnabled(False); self.canon.setEnabled(False)
        self.status = QLabel('Choose a book or create one.'); layout.addWidget(self.status)
        self.books.currentItemChanged.connect(self.select_book)
        self.chapters.currentItemChanged.connect(self.select_chapter)
        self.timer = QTimer(self); self.timer.timeout.connect(self.autosave); self.timer.start(2000)
        self.load_books()
        self.command_server = AuthorCommandServer(self)
        self.command_server.intentReady.connect(self.handle_author_intent)
        self.command_server.start()

    def handle_author_intent(self, intent):
        """Execute a previously validated request in the GUI thread only."""
        if not self.isVisible():
            self.status.setText('Author command ignored: Author Bay is not visible.')
            return
        action = intent.get('action')
        if action == 'review':
            self.toolkit.review_depth.setCurrentIndex(
                1 if intent.get('depth') == 'deep' else 0)
            self.toolkit.start_review(intent['scope'])
        elif action == 'read':
            if intent['scope'] == 'book':
                self.toolkit.read_book()
            else:
                self.toolkit.read_aloud()
        elif action == 'cancel_review':
            self.toolkit.cancel_review()
        elif action == 'pause_reading':
            self.toolkit.reader.pause()
        elif action == 'resume_reading':
            self.toolkit.reader.resume()
        elif action == 'stop_reading':
            self.toolkit.reader.stop()
        elif action == 'open_project_map':
            if self.flush():
                self.editor_tabs.setCurrentWidget(self.project_map)
        elif action == 'open_story_atlas':
            if self.flush():
                self.editor_tabs.setCurrentWidget(self.atlas_widget)
        elif action == 'open_master_canon':
            if self.flush():
                self.editor_tabs.setCurrentWidget(self.master_canon_widget)
        elif action == 'open_canon_intelligence':
            if self.flush():
                self.editor_tabs.setCurrentWidget(self.canon_intelligence)

    def action(self, function):
        try:
            return function()
        except Exception as error:
            # Keep the editor contents intact when a disk/database operation fails.
            self.status.setText('Save/action failed: ' + str(error))
            QMessageBox.warning(self, 'Author', str(error))
            return False

    def load_books(self):
        self.books.clear()
        for book in self.store.books():
            item = QListWidgetItem(book['title']); item.setData(256, book['id']); self.books.addItem(item)

    def flush(self):
        def save():
            if self.chapter_id is not None:
                self.store.save(self.chapter_id, self.editor.toPlainText())
            if self.book_id is not None:
                self.store.save_canon(self.book_id, self.canon.toPlainText())
            self.toolkit.save_current()
            if not self.project_map.save_pending():
                return False
            self.status.setText('Saved locally. ' + str(len(self.editor.toPlainText().split())) + ' words.')
            return True
        return self.action(save)

    def autosave(self):
        if self.book_id is not None:
            self.flush()

    def select_book(self, item, previous=None):
        if not self.flush():
            self.books.blockSignals(True); self.books.setCurrentItem(previous); self.books.blockSignals(False)
            return
        self.chapter_id = None; self.editor.clear(); self.editor.setEnabled(False)
        self.book_id = item.data(256) if item else None
        self.canon.setEnabled(item is not None)
        self.canon.setPlainText(self.store.canon(self.book_id) if item else '')
        self.load_chapters()
        self.toolkit.set_book(self.book_id)
        self.project_map.set_book(self.book_id)
        self.atlas_widget.set_book(self.book_id)
        self.master_canon_widget.set_book(self.book_id)
        self.canon_intelligence.set_book(self.book_id)

    def load_chapters(self):
        self.chapters.blockSignals(True); self.chapters.clear()
        if self.book_id is not None:
            for chapter in self.store.chapters(self.book_id):
                item = QListWidgetItem(chapter['title']); item.setData(256, chapter['id']); self.chapters.addItem(item)
        self.chapters.blockSignals(False)

    def select_chapter(self, item, previous=None):
        if not self.flush():
            self.chapters.blockSignals(True); self.chapters.setCurrentItem(previous); self.chapters.blockSignals(False)
            return
        self.chapter_id = item.data(256) if item else None
        self.editor.setEnabled(item is not None)
        self.editor.setPlainText(self.store.chapter(self.chapter_id)['content'] if item else '')

    def project_map_status(self, message):
        if message.startswith('Chapter plan save failed:'):
            self.status.setText(message)

    def on_tab_changed(self, index):
        target = self.editor_tabs.widget(index)
        if (target in (self.project_map, self.atlas_widget,
                       self.master_canon_widget)
                and self.book_id is not None and self.flush()):
            target.refresh()

    def jump_to_chapter_id(self, chapter_id):
        """Navigate only within the selected book; never open unrelated books."""
        if not self.flush():
            return
        for index in range(self.chapters.count()):
            if self.chapters.item(index).data(Qt.UserRole) == chapter_id:
                self.chapters.setCurrentRow(index)
                self.editor_tabs.setCurrentWidget(self.editor)
                self.editor.setFocus()
                return
        self.status.setText('Chapter is no longer in the selected book.')

    def jump_to_canon_source(self, chapter_id, quote, digest):
        """Navigate to a source across books, refusing stale quotation highlights."""
        try:
            chapter = self.store.chapter(int(chapter_id))
        except (ValueError, TypeError):
            self.status.setText('Canon source chapter is missing.')
            return
        if not self.flush():
            return
        book_id = chapter['book_id']
        if self.book_id != book_id:
            for index in range(self.books.count()):
                if self.books.item(index).data(Qt.UserRole) == book_id:
                    self.books.setCurrentRow(index)
                    break
        if self.book_id != book_id:
            self.status.setText('Could not open the source book.')
            return
        self.jump_to_chapter_id(chapter['id'])
        content = self.editor.toPlainText()
        if not quote:
            self.status.setText('Opened referenced chapter. No exact quote was recorded.')
            return
        if (hashlib.sha256(content.encode('utf-8')).hexdigest() != digest
                or quote not in content):
            self.status.setText(
                'Opened source chapter. Canon quotation is outdated or source changed; '
                'nothing was highlighted or edited.'
            )
            return
        start = content.find(quote)
        qt_start = len(content[:start].encode('utf-16-le')) // 2
        qt_end = len(content[:start + len(quote)].encode('utf-16-le')) // 2
        cursor = self.editor.textCursor()
        cursor.setPosition(qt_start)
        cursor.setPosition(qt_end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.status.setText('Selected verified canon quotation. No text changed.')

    def new_book(self):
        title, ok = QInputDialog.getText(self, 'New book', 'Title:')
        if ok and title.strip() and self.flush():
            if self.action(lambda: self.store.create_book(title)) is not False:
                self.load_books(); self.books.setCurrentRow(self.books.count() - 1)

    def new_chapter(self):
        if self.book_id is None:
            return
        title, ok = QInputDialog.getText(self, 'New chapter', 'Title:')
        if ok and title.strip() and self.flush():
            if self.action(lambda: self.store.create_chapter(self.book_id, title)) is not False:
                self.load_chapters(); self.chapters.setCurrentRow(self.chapters.count() - 1)
                self.project_map.refresh()

    def import_text(self):
        if self.book_id is None or not self.flush():
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Import as a new chapter', '', 'Text (*.txt *.md *.markdown)')
        if path and self.action(lambda: self.store.import_text(self.book_id, path)) is not False:
            self.load_chapters(); self.chapters.setCurrentRow(self.chapters.count() - 1)
            self.project_map.refresh()

    def import_docx(self):
        """Confirm a read-only preview before creating a separate new book."""
        if not self.flush():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, 'Import Word manuscript as a new book', '',
            'Word manuscripts (*.docx)'
        )
        if not path:
            return
        try:
            if __package__:
                from .manuscript_import import parse_docx
            else:
                from manuscript_import import parse_docx
            preview = parse_docx(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'DOCX preview', str(error))
            return
        headings = ', '.join(title for title, _ in preview.chapters[:5])
        if len(preview.chapters) > 5:
            headings += ', ...'
        message = (
            f"Book: {preview.title}\n"
            f"Chapters: {len(preview.chapters)} | Words: {preview.word_count}\n"
            f"Detected: {headings}\n\n"
            "Import text only. Word formatting, pictures, annotations, and "
            "tracked changes are not imported. Chapter breaks use Heading 1; "
            "without them the entire document becomes one chapter.\n\n"
            "Create a NEW book? Your current manuscripts will not be overwritten."
        )
        if QMessageBox.question(
            self, 'Preview Word manuscript', message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        book_id = self.action(
            lambda: self.store.import_docx(path, preview.fingerprint)
        )
        if book_id is False:
            return
        self.load_books()
        for index in range(self.books.count()):
            if self.books.item(index).data(Qt.UserRole) == book_id:
                self.books.setCurrentRow(index)
                break
        self.status.setText(
            f"Imported {len(preview.chapters)} chapters into a new book. "
            "Your previous library is unchanged."
        )

    def import_bundle(self):
        if not self.flush():
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Import Author library', '', 'Author library (*.json)')
        if path:
            added = self.action(lambda: self.store.import_bundle(path))
            if added is not False:
                self.load_books()
                self.status.setText(f'Imported {added} books. Existing writing preserved.')

    def restore(self):
        if self.chapter_id is None or not self.flush():
            return
        versions = self.store.snapshots(self.chapter_id)
        labels = [str(row['id']) + ' • ' + row['created'] for row in versions]
        if not labels:
            self.status.setText('No previous versions yet.'); return
        label, ok = QInputDialog.getItem(self, 'Restore snapshot', 'Previous version:', labels, 0, False)
        if ok and QMessageBox.question(self, 'Restore', 'Restore this version? The current text is kept in history.') == QMessageBox.Yes:
            content = self.action(lambda: self.store.restore(self.chapter_id, versions[labels.index(label)]['id']))
            if content is not False:
                self.editor.setPlainText(content)

    def toggle_focus(self):
        focus = self.books.isVisible()
        self.books.setVisible(not focus)
        self.chapters.setVisible(not focus)
        self.focus_button.setText('Exit focus' if focus else 'Focus')
        self.status.setText('Focus writing mode' if focus else 'Writing desk')

    def author_review_requested(self, text):
        # Hosting desktop attaches the Webbie review hook. Standalone Author
        # deliberately never sends writing to an AI or an external service.
        callback = getattr(self, 'show_webbie_review', None)
        if callback is None:
            self.status.setText('Open Author through The Web to review selected text with Webbie.')
        else:
            callback(text)

    def apply_revised_passage(self):
        """Review a pasted Webbie suggestion against exactly selected source.

        No autonomous AI edit. Save is transactional and snapshots prior text.
        """
        if self.chapter_id is None or not self.flush():
            return
        cursor = self.editor.textCursor()
        old = cursor.selectedText().replace('\u2029', '\n')
        if not old.strip():
            QMessageBox.information(self, 'Reviewed rewrite',
                                    'Highlight the exact original passage you want to replace.')
            return
        proposed, ok = QInputDialog.getMultiLineText(
            self, 'Reviewed rewrite', 'Paste Webbie’s proposed replacement text:', old
        )
        if not ok or proposed == old:
            return
        original = self.store.chapter(self.chapter_id)['content']
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if self.editor.toPlainText() != original:
            QMessageBox.warning(self, 'Revision changed',
                                'The manuscript has changed. Save and select the passage again.')
            return
        if original[start:end] != old:
            QMessageBox.warning(self, 'Revision conflict',
                                'Selection no longer matches the saved text. No edits were made.')
            return
        confirmation = QMessageBox.question(
            self, 'Approve manuscript revision',
            'Replace the selected passage? The previous chapter will remain in revision history.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirmation != QMessageBox.Yes:
            return
        updated = original[:start] + proposed + original[end:]
        if self.action(lambda: self.store.save(self.chapter_id, updated)) is False:
            return
        self.editor.setPlainText(updated)
        self.status.setText('Approved revision saved. Prior version preserved in snapshots.')

    def current_chapter(self):
        if self.chapter_id is None:
            return None
        return self.store.chapter(self.chapter_id)

    def webbie_context(self):
        # Titles only; manuscript, chapter text and private notes stay local.
        book = next((r for r in self.store.books() if r['id'] == self.book_id), None)
        selected = self.current_chapter()
        parts = [book['title'] if book else 'No book selected']
        if selected is not None:
            parts.append('Chapter: ' + selected['title'])
        return ' | '.join(parts)

    def jump_to_search_result(self, hit):
        if not self.flush():
            return
        for index in range(self.books.count()):
            if self.books.item(index).data(Qt.UserRole) == hit['book_id']:
                self.books.setCurrentRow(index)
                break
        kind = hit['kind']
        if kind == 'chapter':
            for index in range(self.chapters.count()):
                if self.chapters.item(index).data(Qt.UserRole) == hit['item_id']:
                    self.chapters.setCurrentRow(index)
                    break
        elif kind == 'story':
            for index in range(self.toolkit.story_list.count()):
                if self.toolkit.story_list.item(index).data(Qt.UserRole) == hit['item_id']:
                    self.toolkit.story_list.setCurrentRow(index)
                    break
        elif kind == 'reference':
            for index in range(self.toolkit.reference_list.count()):
                if self.toolkit.reference_list.item(index).data(Qt.UserRole) == hit['item_id']:
                    self.toolkit.reference_list.setCurrentRow(index)
                    break

    def jump_to_review_segment(self, section):
        """Highlight only the original, hash-verified review source segment."""
        try:
            book_id, chapter_id = int(section['book_id']), int(section['item_id'])
            start, end = int(section['start']), int(section['end'])
            expected = section['chapter_sha256']
        except (KeyError, ValueError, TypeError):
            self.status.setText('Review link is invalid. No text was selected.')
            return
        if self.book_id != book_id or not self.flush():
            self.status.setText('Select the reviewed book and save changes first.')
            return
        try:
            chapter = self.store.chapter(chapter_id)
        except ValueError:
            self.status.setText('The linked chapter no longer exists.')
            return
        content = chapter['content']
        if (hashlib.sha256(content.encode('utf-8')).hexdigest() != expected
                or not 0 <= start < end <= len(content)):
            self.status.setText(
                'Review section is outdated after edits. '
                'Open the chapter normally or request a new review.')
            return
        self.jump_to_search_result({
            'kind': 'chapter', 'book_id': book_id, 'item_id': chapter_id})
        if self.chapter_id != chapter_id or self.editor.toPlainText() != content:
            self.status.setText('Could not select original review section safely.')
            return
        # QTextCursor positions count UTF-16 units, unlike Python string
        # indexing. Convert offsets so emoji and astral characters do not
        # silently shift the highlighted evidence range.
        qt_start = len(content[:start].encode('utf-16-le')) // 2
        qt_end = len(content[:end].encode('utf-16-le')) // 2
        cursor = self.editor.textCursor()
        cursor.setPosition(qt_start)
        cursor.setPosition(qt_end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor_tabs.setCurrentWidget(self.editor)
        self.editor.ensureCursorVisible()
        self.status.setText('Selected exact section from Webbie review. No edits made.')

    def backup(self):
        if not self.flush():
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Backup library', 'author-backup.sqlite3', 'SQLite (*.sqlite3)')
        if path:
            if self.action(lambda: self.store.backup(path)) is not False:
                self.status.setText('Library backup saved.')

    def closeEvent(self, event):
        if not self.canon_intelligence.shutdown():
            self.status.setText(
                'Canon Intelligence is cancelling the running local review. '
                'Close Author after the model request finishes.')
            event.ignore()
            return
        if not self.toolkit.shutdown():
            self.status.setText(
                'Webbie is stopping the active review or narration. '
                'Close Author again when the task has finished.')
            event.ignore()
            return
        if self.flush():
            self.command_server.stop()
            self.timer.stop(); self.store.close(); event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv); app.setApplicationName('Spider Author')
    window = AuthorWindow(); window.show(); sys.exit(app.exec_())


if __name__ == '__main__':
    main()
