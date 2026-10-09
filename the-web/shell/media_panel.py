"""Native Media workspace transport; work happens outside the GUI thread."""
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from media_transport import control, discover_players, player_state


class MediaWorker(QThread):
    result = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, player=None, action=None, parent=None):
        super().__init__(parent); self.player, self.action = player, action

    def run(self):
        try:
            if self.action: control(self.player, self.action)
            names = discover_players()
            # Read only the explicitly chosen player, with bounded calls.
            selected = self.player if self.player in names else None
            state = player_state(selected) if selected else ''
            self.result.emit((names, selected, state))
        except (RuntimeError, ValueError) as error:
            self.failed.emit(str(error))


class MediaPanel(QWidget):
    def __init__(self, launch):
        super().__init__(); self.worker = None
        layout = QVBoxLayout(self); layout.addWidget(QLabel('Media playback'))
        open_button = QPushButton('Open Spider Media Center'); open_button.setMinimumHeight(44)
        open_button.clicked.connect(launch); layout.addWidget(open_button)
        self.players = QComboBox(); self.players.setMinimumHeight(40); layout.addWidget(self.players)
        self.players.activated.connect(lambda index: self.refresh())
        self.status = QLabel('Open a player, then refresh. Choose which player to control.'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.refresh_button = QPushButton('Refresh players'); self.refresh_button.setMinimumHeight(44)
        self.refresh_button.clicked.connect(self.refresh); layout.addWidget(self.refresh_button)
        self.controls = []; row = QHBoxLayout(); layout.addLayout(row)
        for text, action in [('Previous', 'Previous'), ('−10 s', 'Back10'), ('Play / Pause', 'PlayPause'), ('+10 s', 'Forward10'), ('Next', 'Next'), ('Stop', 'Stop')]:
            button = QPushButton(text); button.setMinimumHeight(44); button.setEnabled(False)
            button.clicked.connect(lambda checked=False, name=action: self.refresh(name)); row.addWidget(button); self.controls.append(button)
        note = QLabel('These controls work with players that support Linux media controls. A player that does not appear keeps its own controls.'); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(1)

    def refresh(self, action=None):
        if self.worker and self.worker.isRunning(): return
        if self.worker: self.worker.deleteLater()
        selected = self.players.currentData()
        self.refresh_button.setEnabled(False); self.players.setEnabled(False)
        for button in self.controls: button.setEnabled(False)
        self.status.setText('Checking media players…')
        self.worker = MediaWorker(selected, action, self)
        self.worker.result.connect(self.render); self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finish); self.worker.start()

    def render(self, result):
        names, selected, state = result
        self.players.clear(); self.players.addItem('Select a player', None)
        for name in names: self.players.addItem(name.removeprefix('org.mpris.MediaPlayer2.'), name)
        if selected: self.players.setCurrentIndex(self.players.findData(selected))
        self.status.setText(state if selected else ('Choose a player above.' if names else 'No compatible media players found. Open a player and refresh.'))

    def failed(self, message):
        self.status.setText(message)

    def finish(self):
        self.refresh_button.setEnabled(True); self.players.setEnabled(True)
        for button in self.controls: button.setEnabled(bool(self.players.currentData()))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning(): event.ignore()
        else: event.accept()
