#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame, QGridLayout, QScrollArea, QTabWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

SPIDER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPIDER_ROOT / 'system'))
from apps import AppUnavailable, media_command
sys.path.insert(0, str(SPIDER_ROOT / 'the-web' / 'shell'))
from workspace_max_native import NativeWorkspaceTools
sys.path.insert(0, str(Path(__file__).resolve().parent))
if __package__:
    from .tools import TOOLS, resolve_tool
    from .ai_panel import StudioAIPanel
    from .band_mixer_panel import BandMixerPanel
    from .release_panel import ReleasePanel
    from .production_board_panel import ProductionBoardPanel
    from .audio_quality_panel import AudioQualityPanel
else:
    from tools import TOOLS, resolve_tool
    from ai_panel import StudioAIPanel
    from band_mixer_panel import BandMixerPanel
    from release_panel import ReleasePanel
    from production_board_panel import ProductionBoardPanel
    from audio_quality_panel import AudioQualityPanel
STUDIO_HOME = Path.home() / 'Documents' / 'Spider Studio'


class StudioButton(QPushButton):
    def __init__(self, text, action):
        super().__init__(text)
        self.setMinimumHeight(52)
        self.clicked.connect(action)


class SpiderStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Spider Studio | Spider OS')
        self.resize(1180, 760)

        self.setStyleSheet("""
            QWidget { background: #0c0a10; color: #eeeaf3; }
            QTabBar::tab { background:#21172d; color:#e9d5ff; padding:8px; }
            QTabBar::tab:selected { background:#4c1d95; }
            QTabWidget::pane, QScrollArea { border:1px solid #4c1d95; }
            QPushButton:disabled { background:#17121d; color:#93869e; border-color:#352543; }
            QMainWindow { background: #0c0a10; color: #eeeaf3; }
            QFrame#sidebar { background: #15111b; border-right: 1px solid #6d28d9; }
            QLabel { color: #eeeaf3; }
            QPushButton {
                background: #21172d;
                color: #f5f0fa;
                border: 1px solid #4c1d95;
                border-radius: 10px;
                padding: 12px;
                text-align: left;
                font-size: 15px;
            }
            QPushButton:hover { background: #342047; border-color: #8b5cf6; }
            QPushButton:pressed { background: #4c1d95; }
        """)

        STUDIO_HOME.mkdir(parents=True, exist_ok=True)
        for name in ('Music', 'Media', 'Artwork'):
            (STUDIO_HOME / name).mkdir(parents=True, exist_ok=True)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(270)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 24, 20, 24)
        side.setSpacing(10)

        logo = QLabel('SPIDER STUDIO')
        logo.setFont(QFont('Sans Serif', 22, QFont.Bold))
        logo.setStyleSheet('color: #a78bfa;')
        side.addWidget(logo)

        subtitle = QLabel('CREATE. BUILD. PLAY.')
        subtitle.setStyleSheet('color: #8f859a;')
        side.addWidget(subtitle)
        side.addSpacing(24)

        side.addWidget(StudioButton('Music Studio', self.launch_music))
        side.addWidget(StudioButton('Spider Media Center', self.launch_media))
        side.addWidget(StudioButton('Artwork', self.open_artwork))
        side.addWidget(StudioButton('Studio Files', self.open_studio_home))
        side.addStretch()

        self.status = QLabel('Checking Spider Studio…')
        self.status.setWordWrap(True)
        self.status.setStyleSheet('color: #a3a3a3;')
        side.addWidget(self.status)

        outer.addWidget(sidebar)

        center = QWidget()
        content = QVBoxLayout(center)
        content.setContentsMargins(50, 48, 50, 48)

        title = QLabel('Spider Studio')
        title.setFont(QFont('Sans Serif', 32, QFont.Bold))
        content.addWidget(title)

        description = QLabel(
            'The creative workspace for Spider OS.\n'
            'Music • Media • Artwork • Webbie'
        )
        description.setFont(QFont('Sans Serif', 16))
        description.setStyleSheet('color: #b6a9c7;')
        content.addWidget(description)
        content.addSpacing(30)

        self.media_status = QLabel()
        self.webbie_status = QLabel()
        self.ollama_status = QLabel()
        for label in (self.media_status, self.webbie_status, self.ollama_status):
            label.setFont(QFont('Sans Serif', 14))
            content.addWidget(label)

        self.tool_tabs = QTabWidget()
        content.addWidget(self.tool_tabs, 1)
        self.ai_panel = StudioAIPanel()
        ai_scroll = QScrollArea()
        ai_scroll.setWidgetResizable(True)
        ai_scroll.setWidget(self.ai_panel)
        self.tool_tabs.addTab(ai_scroll, 'Studio AI')
        # All new identity/instrument logic stays within the tab section. This
        # keeps legacy Studio reconciliation strict and structurally comparable.
        if __package__:
            from .instrument_workbench import InstrumentWorkbench
        else:
            from instrument_workbench import InstrumentWorkbench
        from PyQt5.QtGui import QIcon
        self.setWindowTitle('Spider Audio Studio | Spider OS')
        app_icon = SPIDER_ROOT / 'branding/spider-apps/icons/spider-audio-studio.svg'
        if app_icon.is_file():
            self.setWindowIcon(QIcon(str(app_icon)))
        # Native Spider instrument machine: no external launcher, no replacement DAW.
        self.instrument_workbench = InstrumentWorkbench(self)
        instrument_scroll = QScrollArea()
        instrument_scroll.setWidgetResizable(True)
        instrument_scroll.setWidget(self.instrument_workbench)
        self.tool_tabs.addTab(instrument_scroll, 'Play Instruments')
        self.instrument_page = instrument_scroll
        if __package__:
            from .song_production_panel import SongProductionPanel
        else:
            from song_production_panel import SongProductionPanel
        self.song_production_panel = SongProductionPanel(self.instrument_workbench, self)
        song_scroll = QScrollArea()
        song_scroll.setWidgetResizable(True)
        song_scroll.setWidget(self.song_production_panel)
        self.tool_tabs.addTab(song_scroll, 'Song Arranger & Mixer')
        if __package__:
            from .waveform_edit_panel import WaveformEditPanel
        else:
            from waveform_edit_panel import WaveformEditPanel
        self.waveform_edit_panel = WaveformEditPanel(self)
        waveform_scroll = QScrollArea()
        waveform_scroll.setWidgetResizable(True)
        waveform_scroll.setWidget(self.waveform_edit_panel)
        self.tool_tabs.addTab(waveform_scroll, 'Waveform Editor')
        if __package__:
            from .dj_deck_panel import DJDeckPanel
        else:
            from dj_deck_panel import DJDeckPanel
        self.dj_deck_panel = DJDeckPanel(self)
        dj_scroll = QScrollArea()
        dj_scroll.setWidgetResizable(True)
        dj_scroll.setWidget(self.dj_deck_panel)
        self.tool_tabs.addTab(dj_scroll, 'DJ Decks')
        if __package__:
            from .auto_performer_panel import AutoPerformerPanel
        else:
            from auto_performer_panel import AutoPerformerPanel
        self.auto_performer_panel = AutoPerformerPanel(self)
        auto_scroll = QScrollArea()
        auto_scroll.setWidgetResizable(True)
        auto_scroll.setWidget(self.auto_performer_panel)
        self.tool_tabs.addTab(auto_scroll, 'Auto Performer · Scores & TAB')
        self.auto_performer_page = auto_scroll
        if __package__:
            from .score_timeline_panel import ScoreTimelinePanel
        else:
            from score_timeline_panel import ScoreTimelinePanel
        self.score_timeline_panel = ScoreTimelinePanel(self.auto_performer_panel.apply_edited_score, self)
        self.tool_tabs.addTab(self.score_timeline_panel, 'Performance Note Editor')
        self.auto_performer_panel.attach_editor(
            self.score_timeline_panel,
            lambda: self.tool_tabs.setCurrentWidget(self.score_timeline_panel))
        # Explicit hardware-only recording stays inside the original Studio,
        # never as a separate launcher or automatic background microphone.
        if __package__:
            from .audio_capture_panel import AudioCapturePanel
        else:
            from audio_capture_panel import AudioCapturePanel
        self.audio_capture_panel = AudioCapturePanel(self)
        capture_scroll = QScrollArea()
        capture_scroll.setWidgetResizable(True)
        capture_scroll.setWidget(self.audio_capture_panel)
        self.tool_tabs.addTab(capture_scroll, 'Record Audio · Multitrack')
        self.audio_capture_page = capture_scroll
        # Owner-selected audio stems can enter the real native mixer directly.
        # No terminal, outside DAW, or automatic microphone access.
        if __package__:
            from .stem_import_panel import StemImportPanel
        else:
            from stem_import_panel import StemImportPanel
        self.stem_import_panel = StemImportPanel(self)
        self.tool_tabs.addTab(self.stem_import_panel, 'Import WAVs · Create Song')
        if __package__:
            from .welcome_panel import StudioWelcome
        else:
            from welcome_panel import StudioWelcome
        self.welcome_panel=StudioWelcome(
            open_import=lambda:self.tool_tabs.setCurrentWidget(
                self.stem_import_panel),
            open_record=lambda:self.tool_tabs.setCurrentWidget(
                self.audio_capture_page),
            open_instruments=lambda:self.tool_tabs.setCurrentWidget(
                self.instrument_page),
            open_session=self.open_existing_session,
            open_recent=self.open_recent_songs,
            parent=self)
        self.tool_tabs.insertTab(0,self.welcome_panel,'Start a Song')
        # Read-only recording inventory inside native Studio; no hardware access.
        if __package__:
            from .recording_audit_panel import RecordingAuditPanel
        else:
            from recording_audit_panel import RecordingAuditPanel
        self.recording_audit_panel = RecordingAuditPanel(self)
        self.tool_tabs.addTab(self.recording_audit_panel, 'Recording Library Audit')
        # Handoff selects a private cue only; never opens a mic or starts sound.
        self.auto_performer_panel.backing_cue_ready.connect(self._handoff_virtual_band)
        self.song_production_panel.backing_cue_ready.connect(self._handoff_virtual_band)


        self.native_max_tools = NativeWorkspaceTools('studio', self)
        self.tool_tabs.addTab(self.native_max_tools, 'Production analysis & tasks')
        # Preserve the owner-reviewed Studio layout while activating the
        # October 11 production, band mixing and quality-control workspaces.
        self.band_mixer_panel = BandMixerPanel(ai_panel=self.ai_panel)
        band_scroll = QScrollArea()
        band_scroll.setWidgetResizable(True)
        band_scroll.setWidget(self.band_mixer_panel)
        self.tool_tabs.addTab(band_scroll, 'Band Mixer')

        self.release_panel = ReleasePanel(band_mixer=self.band_mixer_panel)
        release_scroll = QScrollArea()
        release_scroll.setWidgetResizable(True)
        release_scroll.setWidget(self.release_panel)
        self.tool_tabs.addTab(release_scroll, 'Release Desk')

        self.production_board_panel = ProductionBoardPanel(
            ai_panel=self.ai_panel, band_mixer=self.band_mixer_panel,
            release_panel=self.release_panel, tool_tabs=self.tool_tabs,
        )
        production_scroll = QScrollArea()
        production_scroll.setWidgetResizable(True)
        production_scroll.setWidget(self.production_board_panel)
        self.tool_tabs.addTab(production_scroll, 'Production Board')

        self.quality_panel = AudioQualityPanel(
            production_board=self.production_board_panel,
        )
        quality_scroll = QScrollArea()
        quality_scroll.setWidgetResizable(True)
        quality_scroll.setWidget(self.quality_panel)
        self.tool_tabs.addTab(quality_scroll, 'Audio Quality')
        self.production_board_panel.quality_panel = self.quality_panel
        self.production_board_panel.quality_tab = quality_scroll
        self.tool_buttons = []
        for category, tools in TOOLS.items():
            page = QWidget(); grid = QGridLayout(page)
            for index, tool in enumerate(tools):
                frame = QFrame(); box = QVBoxLayout(frame)
                heading = QLabel(tool[0]); heading.setStyleSheet('font-size:18px; color:#c4b5fd;')
                box.addWidget(heading)
                description = QLabel(tool[1]); description.setWordWrap(True); box.addWidget(description)
                button = QPushButton('Open')
                button.clicked.connect(lambda checked=False, selected=tool: self.launch_tool(selected))
                box.addWidget(button); grid.addWidget(frame, index // 2, index % 2)
                self.tool_buttons.append((tool, button))
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page)
            self.tool_tabs.addTab(scroll, category.replace('&', '&&'))
        refresh = QPushButton('Refresh installed tools'); refresh.clicked.connect(self.refresh_tools)
        content.addWidget(refresh)
        self.refresh_tools()

        content.addSpacing(8)
        note = QLabel(
            'Spider Media Center is the Media module.\n'
            'Webbie remains the resident AI service shared across Spider OS.'
        )
        note.setStyleSheet('color: #82788d;')
        content.addWidget(note)

        footer = QLabel('SPIDER OS  •  YOUR LIFE. ONE WEB.')
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet('color: #625a69;')
        content.addWidget(footer)

        outer.addWidget(center, 1)

        self.tool_tabs.setCurrentWidget(self.welcome_panel)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)
        self.update_status()

    def launch(self, command):
        try:
            subprocess.Popen(command)
            self.status.setText('Launched: ' + ' '.join(command))
            return True
        except Exception as exc:
            self.status.setText(str(exc))
            return False

    def refresh_tools(self):
        installed = 0
        for tool, button in self.tool_buttons:
            available = resolve_tool(tool) is not None
            button.setEnabled(available)
            button.setText('Open' if available else 'Unavailable on this machine')
            installed += int(available)
        self.status.setText(f'{installed} creative tools available.')

    def launch_tool(self, tool):
        command = resolve_tool(tool)
        if command is None:
            self.refresh_tools()
            self.status.setText(f'{tool[0]} is not available on this machine.')
            return
        if self.launch(command):
            self.status.setText(f'Opened {tool[0]}.')

    def open_recent_songs(self):
        """Open local saved session inventory; verifying still occurs on open."""
        if __package__:
            from .saved_songs_dialog import SavedSongsDialog
        else:
            from saved_songs_dialog import SavedSongsDialog
        chooser=SavedSongsDialog(parent=self)
        chooser.exec_()

    def open_existing_session(self):
        """Open the exact existing native verified session mixing dialog."""
        if __package__:
            from .session_mix_dialog import SessionMixDialog
        else:
            from session_mix_dialog import SessionMixDialog
        editor=SessionMixDialog(parent=self)
        editor.exec_()

    def launch_music(self):
        # The music sidebar button must open Spider's REAL native tools, not
        # launch another DAW as a substitute. Ubuntu Studio apps remain
        # available in the preserved installed-tool tabs when needed.
        self.tool_tabs.setCurrentWidget(self.instrument_page)
        self.status.setText('Spider Audio Studio instruments are ready in this window.')

    def media_command(self):
        try:
            return media_command()
        except AppUnavailable:
            return None

    def launch_media(self):
        command = self.media_command()
        if command:
            self.launch(command)
        else:
            self.status.setText('Spider Media Center is not installed. Install a verified media package first.')

    def open_artwork(self):
        self.launch(['xdg-open', str(STUDIO_HOME / 'Artwork')])

    def open_studio_home(self):
        self.launch(['xdg-open', str(STUDIO_HOME)])

    def user_service_active(self, service):
        try:
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', service],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2,
            )
            return result.stdout.strip() == 'active'
        except (OSError, subprocess.TimeoutExpired):
            return False

    def update_status(self):
        media = self.media_command()
        webbie = self.user_service_active('webbie.service')

        self.media_status.setText(
            '● Spider Media Center: INSTALLED'
            if media
            else '○ Spider Media Center: NOT INSTALLED'
        )
        self.webbie_status.setText(
            '● Webbie: ACTIVE' if webbie else '○ Webbie: OFFLINE'
        )

        self.ollama_status.setText(
            '● Ollama: INSTALLED' if shutil.which('ollama') else '○ Ollama: NOT FOUND'
        )


    def _handoff_virtual_band(self, path, rate):
        """Connect both real native virtual-band bays to the recording console."""
        if self.audio_capture_panel.load_generated_cue(path,rate):
            self.tool_tabs.setCurrentWidget(self.audio_capture_page)

    def closeEvent(self, event):
        # Do not destroy a QThread while it is exporting the owner's song or
        # WAV. Preserve the existing MAX worker closure protection as well.
        for panel in (self.native_max_tools, self.song_production_panel,
                      self.waveform_edit_panel, self.dj_deck_panel,
                      self.auto_performer_panel, self.audio_capture_panel,
                      self.stem_import_panel):
            worker = getattr(panel, 'worker', None)
            if worker is not None and worker.isRunning():
                if panel is self.stem_import_panel:
                    self.stem_import_panel.cancel_import()
                if panel is self.audio_capture_panel:
                    self.audio_capture_panel.stop()
                self.status.setText('Finish or safely stop the current recording/export before closing Spider Studio.')
                event.ignore()
                return
        midi = self.instrument_workbench.midi_input
        midi.disconnect()
        if midi.worker is not None and midi.worker.isRunning():
            self.status.setText('MIDI connection is still closing.')
            event.ignore()
            return
        self.instrument_workbench.timer.stop()
        self.waveform_edit_panel.stop_preview()
        self.dj_deck_panel.stop()
        self.auto_performer_panel.stop()
        for audio, _data in list(self.instrument_workbench._voices):
            audio.stop()
        self.instrument_workbench._voices.clear()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Spider Studio')
    app.setOrganizationName('Spider OS')
    window = SpiderStudio()
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
