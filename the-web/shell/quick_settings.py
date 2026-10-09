"""Read-only KDE-friendly Spider OS quick settings.

Do not replace NetworkManager, Bluetooth, power policies or device managers.
The opening panel is safe even when optional command-line tools are missing.
Settings changes remain in KDE's normal permission-managed Settings app.
"""
from pathlib import Path
import re
import shutil
import subprocess

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from gtk_compat import appearance_snapshot
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox

STATUS_COMMANDS = {
    'connection': ('nmcli', '-t', '-f', 'STATE', 'general'),
    'wifi': ('nmcli', '-t', '-f', 'WIFI', 'general'),
    'bluetooth': ('bluetoothctl', 'show'),
    'brightness': ('brightnessctl', '-m'),
    'microphone': ('wpctl', 'get-volume', '@DEFAULT_AUDIO_SOURCE@'),
}


def read_command(args):
    """A fixed argument vector, never shell=True or input taken from the room."""
    tool = shutil.which(args[0])
    if not tool:
        return None
    try:
        result = subprocess.run([tool, *args[1:]], capture_output=True,
                                text=True, timeout=2, check=False)
        return result.stdout[:2048] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def battery_summary(power_supply=Path('/sys/class/power_supply')):
    """Observe only published sysfs power properties, without changing state."""
    try:
        entries = sorted(Path(power_supply).iterdir())
    except OSError:
        return 'Unknown'
    batteries = []
    chargers = []
    for entry in entries[:20]:
        try:
            kind = (entry / 'type').read_text(encoding='ascii').strip()
            if kind == 'Battery':
                percent = (entry / 'capacity').read_text(encoding='ascii').strip()
                if not re.fullmatch(r'\d{1,3}', percent):
                    continue
                percent = min(int(percent), 100)
                status = (entry / 'status').read_text(encoding='ascii').strip()[:32]
                batteries.append(f'{percent}% ({status or "unknown"})')
            elif kind in ('Mains', 'USB', 'USB_C'):
                online = (entry / 'online').read_text(encoding='ascii').strip()
                if online in ('0', '1'):
                    chargers.append(online == '1')
        except (OSError, UnicodeError, ValueError):
            continue
    if batteries:
        return ', '.join(batteries[:3])
    if any(chargers):
        return 'AC power · no battery detected'
    return 'No battery reading (desktop PC or unsupported device)'


def quick_snapshot(runner=read_command, power_supply=Path('/sys/class/power_supply')):
    connection = runner(STATUS_COMMANDS['connection'])
    wifi = runner(STATUS_COMMANDS['wifi'])
    bluetooth = runner(STATUS_COMMANDS['bluetooth'])
    brightness = runner(STATUS_COMMANDS['brightness'])
    microphone = runner(STATUS_COMMANDS['microphone'])
    state = (connection or '').strip().splitlines()[:1]
    wifi_state = (wifi or '').strip().splitlines()[:1]
    if bluetooth:
        match = re.search(r'^\s*Powered:\s*(yes|no)\s*$', bluetooth, re.MULTILINE)
        blue = ('On' if match.group(1) == 'yes' else 'Off') if match else 'Adapter status unknown'
    else:
        blue = 'Unavailable (or no Bluetooth adapter)'
    bright = 'Unavailable'
    if brightness:
        match = re.search(r'\b(\d{1,3})%', brightness)
        if match:
            bright = str(min(int(match.group(1)), 100)) + '%'
    mic = 'Unknown (WirePlumber source not reported)'
    if microphone:
        match = re.search(r'Volume:\s*([0-9]+(?:\.[0-9]+)?)', microphone)
        if match:
            mic_level = max(0,min(100,round(float(match.group(1))*100)))
            mic = ('Muted' if '[MUTED]' in microphone else 'Available') + f' · {mic_level}%'
    snapshot = {
        'Network': state[0][:70] if state else 'NetworkManager status unavailable',
        'Wi-Fi radio': wifi_state[0][:70] if wifi_state else 'Unknown',
        'Bluetooth': blue,
        'Microphone': mic,
        'Power': battery_summary(power_supply),
        'Brightness': bright,
    }
    snapshot.update(appearance_snapshot())
    return snapshot


def settings_command():
    for name in ('systemsettings', 'systemsettings6', 'systemsettings5'):
        found = shutil.which(name)
        if found:
            return [found]
    return None


def open_kde_settings():
    command = settings_command()
    if not command:
        raise RuntimeError('KDE System Settings is not installed')
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as error:
        raise RuntimeError('Could not open KDE System Settings') from error


class QuickSettingsWorker(QThread):
    ready = pyqtSignal(object)
    def run(self):
        self.ready.emit(quick_snapshot())


class QuickSettingsPanel(QWidget):
    """Fast-access status, while KDE retains all privileged device controls."""
    def __init__(self, parent=None, appearance_reader=None, appearance_writer=None):
        super().__init__(parent)
        self._appearance_reader = appearance_reader
        self._appearance_writer = appearance_writer
        self.setWindowTitle('Spider OS · Quick Settings')
        self.setObjectName('spiderQuickSettings')
        layout = QVBoxLayout(self)
        title = QLabel('Quick Settings')
        title.setStyleSheet('font-weight:bold;font-size:17px;')
        layout.addWidget(title)
        self.status = {}
        for key in ('Network', 'Wi-Fi radio', 'Bluetooth', 'Microphone', 'Power', 'Brightness',
                    'KDE colors', 'GTK 3', 'GTK 4'):
            label = QLabel(key + ': Checking…')
            label.setWordWrap(True)
            label.setTextFormat(Qt.PlainText)
            layout.addWidget(label)
            self.status[key] = label
        appearance_row = QHBoxLayout()
        appearance_row.addWidget(QLabel('The Web appearance'))
        self.appearance_selector = QComboBox()
        self.appearance_selector.setAccessibleName('The Web appearance')
        self.appearance_selector.addItem('Dark violet (default)', 'dark')
        self.appearance_selector.addItem('Light violet', 'light')
        saved = appearance_reader() if callable(appearance_reader) else 'dark'
        if saved not in ('dark', 'light'):
            saved = 'dark'
        self._appearance_value = saved
        self.appearance_selector.setCurrentIndex(self.appearance_selector.findData(saved))
        self.appearance_selector.setEnabled(callable(appearance_writer))
        self.appearance_selector.currentIndexChanged.connect(self.choose_appearance)
        appearance_row.addWidget(self.appearance_selector)
        layout.addLayout(appearance_row)
        controls = QHBoxLayout()
        self.refresh_button = QPushButton('Refresh')
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)
        self.settings_button = QPushButton('Open KDE Settings')
        self.settings_button.clicked.connect(self.open_settings)
        controls.addWidget(self.settings_button)
        layout.addLayout(controls)
        self.help = QLabel('KDE/GTK entries show configured preferences, not guaranteed app appearance. GTK 4/libadwaita may use the desktop color-scheme portal. Changes to KDE and GTK still belong in system settings.')
        self.help.setWordWrap(True)
        self.help.setTextFormat(Qt.PlainText)
        layout.addWidget(self.help)
        self.worker = None
        self.refresh()

    def choose_appearance(self, index):
        candidate = self.appearance_selector.itemData(index)
        if candidate not in ('dark', 'light') or not callable(self._appearance_writer):
            return
        try:
            self._appearance_writer(candidate)
        except (OSError, ValueError, RuntimeError) as error:
            self.help.setText('Appearance not changed: ' + str(error))
            self.appearance_selector.blockSignals(True)
            self.appearance_selector.setCurrentIndex(
                self.appearance_selector.findData(self._appearance_value))
            self.appearance_selector.blockSignals(False)
        else:
            self._appearance_value = candidate
            self.help.setText('The Web appearance saved. KDE, GTK and other apps remain unchanged.')

    def refresh(self):
        if self.worker and self.worker.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.worker = QuickSettingsWorker(self)
        self.worker.ready.connect(self.show_snapshot)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.start()

    def show_snapshot(self, snapshot):
        for key, label in self.status.items():
            label.setText(key + ': ' + str(snapshot.get(key, 'Unknown'))[:160])

    def open_settings(self):
        try:
            open_kde_settings()
        except RuntimeError as error:
            self.help.setText(str(error))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
