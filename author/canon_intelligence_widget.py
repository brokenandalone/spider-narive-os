"""On-demand GUI for locally grounded, writer-approved Canon Intelligence."""
import threading
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget
)
if __package__:
    from .canon_intelligence import CanonIntelligence, current_source
    from .review_engine import ReviewCancelled
else:
    from canon_intelligence import CanonIntelligence, current_source
    from review_engine import ReviewCancelled


class CanonIntelligenceWorker(QThread):
    progress = pyqtSignal(str)
    finishedReport = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, chapters, approved_claims, scope, parent=None):
        super().__init__(parent)
        self.chapters = [dict(row) for row in chapters]
        self.claims = [dict(row) for row in approved_claims]
        self.scope = scope
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def run(self):
        try:
            report = CanonIntelligence().review(
                self.chapters, self.claims, scope=self.scope,
                progress=self.progress.emit, cancelled=self.cancelled
            )
            if self.cancelled.is_set():
                self.failed.emit('Cancelled. Your manuscript and canon are unchanged.')
            else:
                self.finishedReport.emit(report)
        except ReviewCancelled:
            self.failed.emit('Cancelled. No changes were made.')
        except Exception as error:
            self.failed.emit('Canon review failed: ' + str(error))


class CanonIntelligenceWidget(QWidget):
    sourceRequested = pyqtSignal(int, str, str)

    def __init__(self, store, current_chapter, save_editor, parent=None):
        super().__init__(parent)
        self.store = store
        self.current_chapter = current_chapter
        self.save_editor = save_editor
        self.book_id = None
        self.session_book = None
        self.worker = None
        self.report = None

        root = QVBoxLayout(self)
        title = QLabel('CANON INTELLIGENCE / Webbie evidence-linked review')
        root.addWidget(title)
        warning = QLabel(
            'Runs only when requested. Webbie checks the saved manuscript against '
            'Established Master Canon. Suggestions are NOT verified canon or confirmed '
            'errors. Only exact passage quotes are accepted. The source remains local.'
        )
        warning.setWordWrap(True)
        root.addWidget(warning)

        bar = QHBoxLayout()
        self.chapter_button = QPushButton('Compare current chapter')
        self.chapter_button.clicked.connect(lambda *_: self.start_review('chapter'))
        bar.addWidget(self.chapter_button)
        self.book_button = QPushButton('Compare entire book')
        self.book_button.clicked.connect(lambda *_: self.start_review('book'))
        bar.addWidget(self.book_button)
        self.cancel_button = QPushButton('Cancel review')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_review)
        bar.addWidget(self.cancel_button)
        root.addLayout(bar)

        self.status = QLabel('Select a book, then start a comparison.')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self.show_finding)
        root.addWidget(self.results, 2)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        root.addWidget(self.details, 2)
        actions = QHBoxLayout()
        self.open_button = QPushButton('Open verified source')
        self.open_button.clicked.connect(self.open_source)
        actions.addWidget(self.open_button)
        self.propose_button = QPushButton('Save selected idea as Proposed')
        self.propose_button.clicked.connect(self.save_proposal)
        actions.addWidget(self.propose_button)
        root.addLayout(actions)
        self.open_button.setEnabled(False)
        self.propose_button.setEnabled(False)

    def set_book(self, book_id):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
        self.book_id = book_id
        self.report = None
        self.results.clear()
        self.details.clear()
        self.status.setText(
            'Select a chapter or compare the entire book.' if book_id is not None
            else 'Select a book, then start a comparison.'
        )
        self.open_button.setEnabled(False)
        self.propose_button.setEnabled(False)

    def _finish_worker(self):
        self.chapter_button.setEnabled(True)
        self.book_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def start_review(self, scope):
        if self.worker and self.worker.isRunning():
            self.status.setText('A Canon Intelligence comparison is already running.')
            return False
        if self.book_id is None:
            self.status.setText('Select a book before starting a review.')
            return False
        if not self.save_editor():
            self.status.setText('Save the current draft before starting a canon review.')
            return False
        if scope == 'chapter':
            chapter = self.current_chapter()
            if not chapter or chapter['book_id'] != self.book_id:
                self.status.setText('Choose an active chapter first.')
                return False
            sources = [dict(chapter)]
        elif scope == 'book':
            sources = [dict(chapter) for chapter in self.store.chapters(self.book_id)]
        else:
            return False
        sources = [r for r in sources if r['content']]
        if not sources:
            self.status.setText('No nonempty manuscript chapters to compare.')
            return False
        # Claim retrieval and SQLite access occur ONLY in the Qt GUI thread.
        # The worker receives immutable copies, and reads no database handles.
        claims = [
            dict(row) for row in self.store.master_canon.claims(
                include_all=True, status='established'
            )
        ]
        if not claims:
            self.status.setText(
                'No approved Master Canon yet. Establish canon facts manually first.'
            )
            return False
        self.report = None
        self.results.clear()
        self.details.clear()
        self.session_book = self.book_id
        self.worker = CanonIntelligenceWorker(sources, claims, scope, self)
        self.worker.progress.connect(self.status.setText)
        self.worker.finishedReport.connect(self.display_report)
        self.worker.failed.connect(self.review_failed)
        self.worker.finished.connect(self._finish_worker)
        self.chapter_button.setEnabled(False)
        self.book_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText('Comparing against approved Master Canon locally...')
        self.worker.start()
        return True

    def cancel_review(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status.setText('Stopping comparison after the active model request.')

    def review_failed(self, message):
        self.report = None
        self.results.clear()
        self.details.setPlainText(message)
        self.status.setText(message)

    def display_report(self, report):
        if self.session_book != self.book_id:
            self.status.setText('Review discarded: the selected book changed.')
            return
        self.report = report
        self.results.clear()
        for index, finding in enumerate(report['findings']):
            label = 'POSSIBLE CONFLICT' if finding['kind'] == 'possible_conflict' else 'UNAPPROVED IDEA'
            subject = finding.get('canon_title', finding.get('title', ''))
            item = QListWidgetItem(
                f"{label} | {finding['chapter_title']} | {subject}"
            )
            item.setData(Qt.UserRole, index)
            self.results.addItem(item)
        self.status.setText(
            f"{report['chapters_examined']} chapters, "
            f"{report['sections_examined']} sections examined | "
            f"{report['established_claims_considered']}/"
            f"{report['established_claims_available']} established facts "
            f"shortlisted | {len(report['findings'])} quote-checked suggestions."
        )
        self.details.setPlainText(report['limitations'])
        if self.results.count():
            self.results.setCurrentRow(0)

    def _selected(self):
        if not self.report:
            return None
        item = self.results.currentItem()
        if item is None:
            return None
        index = item.data(Qt.UserRole)
        items = self.report['findings']
        return items[index] if isinstance(index, int) and 0 <= index < len(items) else None

    def show_finding(self, *_):
        row = self._selected()
        self.open_button.setEnabled(row is not None)
        self.propose_button.setEnabled(
            row is not None and row['kind'] == 'proposed_idea'
        )
        if row is None:
            return
        lines = [
            'SUGGESTION / NOT A CANON VERDICT',
            'Chapter: ' + row['chapter_title'],
            'Exact source excerpt: ' + row['quote'],
        ]
        if row['kind'] == 'possible_conflict':
            lines += [
                'Approved canon reference: ' + row['canon_title'],
                'Possible problem: ' + row['explanation'],
                'Only the quote and claim ID were checked, not the interpretation.'
            ]
        else:
            lines += [
                'Suggested title: ' + row['title'],
                'Category: ' + row['category'],
                'Unapproved proposed statement: ' + row['statement'],
                'Saving places this in Proposed, never Established.'
            ]
        if not current_source(self.store, row):
            lines.append('WARNING: Saved chapter changed. Rerun review to use this result.')
            self.propose_button.setEnabled(False)
        self.details.setPlainText('\n\n'.join(lines))

    def open_source(self):
        row = self._selected()
        if row is None or not self.save_editor():
            return
        if not current_source(self.store, row):
            QMessageBox.warning(
                self, 'Canon Intelligence',
                'Source text changed since the review. Rerun before using this citation.'
            )
            return
        self.sourceRequested.emit(
            row['chapter_id'], row['quote'], row['chapter_digest']
        )

    def save_proposal(self):
        row = self._selected()
        if row is None or row['kind'] != 'proposed_idea':
            return
        if not self.save_editor() or not current_source(self.store, row):
            QMessageBox.warning(
                self, 'Canon Intelligence',
                'The source changed after review. Nothing saved; review it again.'
            )
            return
        if QMessageBox.question(
            self, 'Save only as Proposed',
            'Save this unverified AI idea in Master Canon as PROPOSED? '
            'It will NOT become established canon or change your manuscript.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        # Recheck after the confirmation dialog in case event-loop saves ran.
        if not current_source(self.store, row):
            QMessageBox.warning(
                self, 'Canon Intelligence', 'Source changed; proposal was not saved.'
            )
            return
        try:
            claim_id = self.store.master_canon.add(
                title=row['title'], statement=row['statement'],
                book_id=row['book_id'], chapter_id=row['chapter_id'],
                category=row['category'], status='proposed',
                source_quote=row['quote']
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Canon Intelligence', str(error))
            return
        self.status.setText(
            f'Saved idea #{claim_id} as PROPOSED only. '
            'Review it in Master Canon before establishing.'
        )
        self.propose_button.setEnabled(False)

    def shutdown(self):
        if self.worker and self.worker.isRunning():
            self.cancel_review()
            return False
        return True
