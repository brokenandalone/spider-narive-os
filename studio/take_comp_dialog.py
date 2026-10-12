"""Human-selected Take Comp Lab for isolated instrument and vocal performances."""
from pathlib import Path
import threading

from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton,
    QSpinBox, QVBoxLayout,
)

if __package__:
    from .multitrack import ROLES, SessionError
    from .take_comp import _read_layout, render_take_comp, PRESETS, NON_PERFORMANCE
    from .take_comp_library import inspect_take_comp
else:
    from multitrack import ROLES, SessionError
    from take_comp import _read_layout, render_take_comp, PRESETS, NON_PERFORMANCE
    from take_comp_library import inspect_take_comp


class CompWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, edits, role, fade):
        super().__init__(QApplication.instance())
        self.edits = [dict(x) for x in edits]
        self.role, self.fade = role, fade
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            output = render_take_comp(self.edits, role=self.role,
                                      fade_ms=self.fade, stop=self.stop)
            self.result.emit(str(output),
                             "Private comp finished. Check alignment and tone before adding.")
        except (SessionError, OSError, ValueError) as error:
            self.result.emit("", str(error))


class TakeCompDialog(QDialog):
    """Prepare one honest independent recording role, not synthetic stems."""

    take_accepted = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Studio: Take Comp Lab")
        self.resize(770, 640)
        self.edits = []
        self.worker = None
        self.output = None
        self.completed_role = None

        outer = QVBoxLayout(self)
        info = QLabel(
            "Build one time-aligned guitar, vocal, bass, drum or keyboard track from "
            "sections of ALREADY isolated recordings. A full-song WAV cannot be turned "
            "into an independent part simply by cropping it. All inputs must share "
            "the same PCM format; original recordings remain unchanged."
        )
        info.setWordWrap(True)
        outer.addWidget(info)
        fields = QFormLayout()
        self.role = QComboBox()
        for name in ROLES:
            if name not in NON_PERFORMANCE:
                self.role.addItem(name.replace("_", " ").title(), name)
        self.role.setCurrentIndex(self.role.findData("rhythm_guitar"))
        fields.addRow("Independent performance role", self.role)
        source_row = QHBoxLayout()
        self.source = QLineEdit()
        self.source.setPlaceholderText("Original isolated PCM WAV")
        self.choose = QPushButton("Browse WAV")
        self.choose.clicked.connect(self.choose_file)
        source_row.addWidget(self.source)
        source_row.addWidget(self.choose)
        fields.addRow("Recorded take", source_row)
        self.source_in = QSpinBox()
        self.source_in.setRange(0, 600000)
        self.source_in.setSuffix(" ms")
        self.source_out = QSpinBox()
        self.source_out.setRange(1, 600000)
        self.source_out.setValue(5000)
        self.source_out.setSuffix(" ms")
        self.timeline_start = QSpinBox()
        self.timeline_start.setRange(0, 600000)
        self.timeline_start.setSuffix(" ms")
        fields.addRow("Source region from", self.source_in)
        fields.addRow("Source region to", self.source_out)
        fields.addRow("Place at project time", self.timeline_start)
        self.fade = QComboBox()
        for value in PRESETS:
            self.fade.addItem(f"{value} ms" if value else "No fade", value)
        self.fade.setCurrentIndex(self.fade.findData(10))
        fields.addRow("Clip-edge fade", self.fade)
        outer.addLayout(fields)

        region_actions = QHBoxLayout()
        self.add = QPushButton("Add selected region")
        self.add.clicked.connect(self.add_region)
        self.remove = QPushButton("Remove selected region")
        self.remove.clicked.connect(self.remove_region)
        region_actions.addWidget(self.add)
        region_actions.addWidget(self.remove)
        outer.addLayout(region_actions)
        self.regions = QListWidget()
        outer.addWidget(self.regions)
        self.status = QLabel(
            "Select real performance ranges. Regions may leave silence but must not overlap."
        )
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        actions = QHBoxLayout()
        self.build = QPushButton("Render new role-specific WAV")
        self.build.clicked.connect(self.render)
        self.stop = QPushButton("Cancel comp rendering")
        self.stop.clicked.connect(self.cancel)
        self.stop.setEnabled(False)
        self.listen = QPushButton("Listen to rendered comp")
        self.listen.clicked.connect(self.audition)
        self.listen.setEnabled(False)
        self.accept = QPushButton("Add this comp to session")
        self.accept.clicked.connect(self.accept_comp)
        self.accept.setEnabled(False)
        self.reopen = QPushButton("Reopen saved Take Comp")
        self.reopen.clicked.connect(self.reopen_comp)
        for button in (self.build, self.stop, self.reopen, self.listen, self.accept):
            actions.addWidget(button)
        outer.addLayout(actions)

    def reopen_comp(self):
        """Only a hash-verified previous comp is eligible for further listening/import."""
        if self.worker is not None:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Reopen a saved Take Comp", str(Path.home() / "Documents/Spider Studio/Music"))
        if not folder:
            return
        try:
            data = inspect_take_comp(folder)
        except (SessionError, OSError, ValueError) as error:
            self.status.setText("Cannot reopen this saved comp: " + str(error))
            return
        self.output = data["path"]
        self.completed_role = data["role"]
        self.role.setCurrentIndex(self.role.findData(data["role"]))
        self.edits.clear()
        self.regions.clear()
        self.listen.setEnabled(True)
        self.accept.setEnabled(True)
        self.status.setText(
            f"Verified {data['edits']} saved region(s), "
            f"{data['duration_seconds']:.1f} seconds in the {data['role']} recording. "
            "Original recording files were not read. Listen before importing. "
            "To change the edit, create a NEW comp from the source takes."
        )

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose genuine isolated recording", str(Path.home()),
            "PCM WAV (*.wav)")
        if path:
            self.source.setText(path)

    def add_region(self):
        if self.worker is not None:
            return
        candidate = {
            "source": self.source.text().strip(),
            "in_ms": self.source_in.value(),
            "out_ms": self.source_out.value(),
            "at_ms": self.timeline_start.value(),
        }
        try:
            _read_layout(self.edits + [candidate], self.role.currentData(),
                         self.fade.currentData())
        except (SessionError, OSError) as error:
            self.status.setText(str(error))
            return
        self.edits.append(candidate)
        self.regions.addItem(
            f"{len(self.edits):02d} | {Path(candidate['source']).name} | "
            f"{candidate['in_ms']}–{candidate['out_ms']} ms => "
            f"project {candidate['at_ms']} ms")
        self.output = None
        self.accept.setEnabled(False)
        self.listen.setEnabled(False)
        self.status.setText(
            "Region added. Render and audition the resulting complete role-specific track.")

    def remove_region(self):
        if self.worker is not None:
            return
        index = self.regions.currentRow()
        if index >= 0:
            self.edits.pop(index)
            self.regions.takeItem(index)
            self.output = None
            self.accept.setEnabled(False)
            self.listen.setEnabled(False)

    def render(self):
        if self.worker is not None:
            return
        try:
            _read_layout(self.edits, self.role.currentData(), self.fade.currentData())
        except (SessionError, OSError) as error:
            self.status.setText(str(error))
            return
        self.output = None
        self.completed_role = None
        self.build.setEnabled(False)
        self.add.setEnabled(False)
        self.remove.setEnabled(False)
        self.choose.setEnabled(False)
        self.reopen.setEnabled(False)
        self.role.setEnabled(False)
        self.stop.setEnabled(True)
        self.listen.setEnabled(False)
        self.accept.setEnabled(False)
        self.status.setText("Reading original takes and rendering a new non-overlapping PCM WAV...")
        self.worker = CompWorker(self.edits, self.role.currentData(), self.fade.currentData())
        self.worker.result.connect(self.rendered)
        self.worker.finished.connect(self.render_finished)
        self.worker.start()

    def rendered(self, path, message):
        self.status.setText(message)
        if path:
            candidate = Path(path)
            if candidate.is_file() and not candidate.is_symlink():
                self.output = candidate
                self.completed_role = self.worker.role if self.worker else self.role.currentData()
                self.listen.setEnabled(True)
                self.accept.setEnabled(True)

    def render_finished(self):
        worker, self.worker = self.worker, None
        self.build.setEnabled(True)
        self.add.setEnabled(True)
        self.remove.setEnabled(True)
        self.choose.setEnabled(True)
        self.reopen.setEnabled(True)
        self.role.setEnabled(True)
        self.stop.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def cancel(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.stop.setEnabled(False)
            self.status.setText("Stopping comp; original WAVs are preserved.")

    def audition(self):
        if self.output and self.output.is_file() and not self.output.is_symlink():
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output))):
                self.status.setText("No audio player was available. Open the comp WAV manually.")

    def accept_comp(self):
        if (self.worker is not None or self.output is None or self.completed_role is None
                or self.output.is_symlink() or not self.output.is_file()):
            self.status.setText("Render and audition a genuine take first.")
            return
        self.take_accepted.emit(
            str(self.output), self.completed_role,
            f"Comped {self.completed_role.replace('_', ' ')} (recorded WAV, review isolation)"
        )
        self.status.setText("Comp sent to multitrack project. Original takes still preserved.")
        self.accept.setEnabled(False)

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
