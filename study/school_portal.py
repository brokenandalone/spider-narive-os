"""School access inside Study. School authentication stays in the browser."""
from pathlib import Path
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QFileDialog

SCHOOL_URL = 'https://my.snhu.edu/'


class SchoolPortal(QWidget):
    def __init__(self, course_folder):
        super().__init__()
        self.course_folder = course_folder
        self.profile = None
        self.views = []
        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        for label, callback in [('My SNHU', self.home), ('Back', self.back),
                                ('Reload', self.reload), ('Open in browser', self.external)]:
            button = QPushButton(label); button.clicked.connect(callback); actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel('Open My SNHU here to sign in. Courses, notes and APA papers stay in Study.')
        self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tabs)

    def ensure_browser(self):
        if self.profile is not None:
            return True
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
        except ImportError:
            self.status.setText('Embedded school access needs python3-pyqt5.qtwebengine and a restarted Spider OS session. Use Open in browser meanwhile.')
            return False
        folder = Path.home() / '.local/share/spider-os/study/browser'
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.profile = QWebEngineProfile('spider-study', self)
        self.profile.setPersistentStoragePath(str(folder))
        self.profile.setCachePath(str(folder / 'cache'))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        self.profile.downloadRequested.connect(self.download)
        portal = self

        class SchoolView(QWebEngineView):
            def createWindow(self, window_type):
                return portal.new_view()

        self.view_class, self.page_class = SchoolView, QWebEnginePage
        return True

    def new_view(self):
        view = self.view_class(self.tabs)
        view.setPage(self.page_class(self.profile, view))
        self.views.append(view)
        index = self.tabs.addTab(view, 'School')
        self.tabs.setCurrentIndex(index)
        view.titleChanged.connect(lambda title, v=view: self.update_title(v, title))
        view.loadFinished.connect(lambda ok: self.status.setText(
            'School portal loaded. Sign in through the school page. Download destinations follow the selected course.' if ok
            else 'The school page could not load here. Try Open in browser for school sign-in.'))
        return view

    def update_title(self, view, title):
        index = self.tabs.indexOf(view)
        if index >= 0:
            self.tabs.setTabText(index, title[:50] or 'School')

    def open(self):
        if self.ensure_browser() and not self.views:
            self.new_view().setUrl(QUrl(SCHOOL_URL))

    def home(self):
        self.open()
        if self.tabs.currentWidget():
            self.tabs.currentWidget().setUrl(QUrl(SCHOOL_URL))

    def back(self):
        if self.tabs.currentWidget():
            self.tabs.currentWidget().back()

    def reload(self):
        if self.tabs.currentWidget():
            self.tabs.currentWidget().reload()

    def external(self):
        # Deliberately open the stable school entry, never copy a transient SSO URL.
        if not QDesktopServices.openUrl(QUrl(SCHOOL_URL)):
            self.status.setText('Could not open the default browser.')

    def close_tab(self, index):
        view = self.tabs.widget(index)
        if view:
            self.tabs.removeTab(index); self.views.remove(view)
            view.stop(); view.deleteLater()

    def download(self, item):
        try:
            folder = Path(self.course_folder()) / 'Downloads'
            folder.mkdir(parents=True, exist_ok=True)
            name = Path(item.path()).name or 'school-download'
            target, _ = QFileDialog.getSaveFileName(self, 'Save school file for the selected course', str(folder / name))
            if not target:
                item.cancel(); return
            item.setPath(target)
            item.finished.connect(lambda: self.status.setText(
                'School file saved.' if item.state() == item.DownloadCompleted
                else 'School download did not complete.'))
            item.accept()
            self.status.setText('School download started.')
        except (OSError, ValueError):
            item.cancel(); self.status.setText('Could not prepare the course download folder.')
