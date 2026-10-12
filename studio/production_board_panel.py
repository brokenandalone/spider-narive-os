"""Spider Studio Production Board: owner-approved song-to-release handoffs.

No action here generates, separates, trains, renders, exports or publishes audio.
All handoffs only populate existing Studio UI fields for later explicit action.
"""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

if __package__:
    from .production_board import (
        ROLES, STEM_ROLES, ProductionError, create_session, list_sessions,
        load_session, save_revision, latest_status, next_action,
    )
    from .song_mix import MixError, valid_wav
    from .multitrack_dialog import MultitrackDialog
else:
    from production_board import (
        ROLES, STEM_ROLES, ProductionError, create_session, list_sessions,
        load_session, save_revision, latest_status, next_action,
    )
    from song_mix import MixError, valid_wav
    from multitrack_dialog import MultitrackDialog

LABELS = {
    'reference_mix': 'Full song reference, not an independent instrument',
    'backing': 'Reviewed instrumental backing WAV',
    'lead_vocal': 'Reviewed lead / converted My Voice WAV',
    'guest_vocal': 'Reviewed guest vocal WAV',
    'rhythm_guitar': 'Reviewed rhythm guitar WAV',
    'lead_guitar': 'Reviewed lead guitar WAV',
    'bass': 'Reviewed bass WAV',
    'drums': 'Reviewed drums WAV',
    'keys': 'Reviewed piano / keys WAV',
    'final_mix': 'Finished, auditioned stereo mix WAV',
}


class ProductionBoardPanel(QWidget):
    def __init__(self, ai_panel=None, band_mixer=None, release_panel=None,
                 tool_tabs=None, parent=None):
        super().__init__(parent)
        self.ai_panel = ai_panel
        self.band_mixer = band_mixer
        self.release_panel = release_panel
        self.tool_tabs = tool_tabs
        self.quality_panel = None
        self.session_id = None
        self.sources = {}
        self.reviewed = {}

        layout = QVBoxLayout(self)
        headline = QLabel('STUDIO PRODUCTION BOARD')
        headline.setStyleSheet('font-size:22px; color:#c4b5fd; font-weight:bold;')
        layout.addWidget(headline)
        intro = QLabel(
            'Keep every song moving from idea to AI take or recording, reviewed stems, '
            'Band Mixer and Release Desk. Every Save creates a NEW private checkpoint. '
            'An AI full-song reference is not eight separate instrument stems. '
            'This board never runs an engine or publishes recordings automatically.'
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        heading = QHBoxLayout()
        self.session_list = QComboBox()
        self.session_list.setObjectName('production_session_list')
        self.session_list.setMinimumWidth(250)
        self.refresh_button = QPushButton('Refresh sessions')
        self.refresh_button.clicked.connect(self.refresh_sessions)
        self.load_button = QPushButton('Load selected session')
        self.load_button.clicked.connect(self.load_selected)
        self.new_button = QPushButton('Start fresh song')
        self.new_button.clicked.connect(self.start_fresh)
        for control in (self.session_list, self.refresh_button,
                        self.load_button, self.new_button):
            heading.addWidget(control)
        layout.addLayout(heading)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Song'))
        self.song_title = QLineEdit('Untitled song')
        self.song_title.setObjectName('production_song_title')
        name_row.addWidget(self.song_title, 1)
        layout.addLayout(name_row)
        self.notes = QPlainTextEdit()
        self.notes.setObjectName('production_notes')
        self.notes.setPlaceholderText('Production directions, arrangement ideas and decisions. Not sent to Webbie.')
        self.notes.setMaximumHeight(100)
        layout.addWidget(self.notes)

        for role in ROLES:
            row = QHBoxLayout()
            field = QLineEdit()
            field.setObjectName('production_' + role)
            field.setPlaceholderText(LABELS[role])
            browse = QPushButton('Choose WAV')
            browse.clicked.connect(lambda checked=False, key=role: self.choose_wav(key))
            row.addWidget(QLabel(role.replace('_', ' ').title()))
            row.addWidget(field, 1)
            row.addWidget(browse)
            if role in STEM_ROLES:
                checked = QCheckBox('I reviewed this isolated WAV')
                checked.setObjectName('production_verified_' + role)
                self.reviewed[role] = checked
                # Editing an approved source revokes approval until it is auditioned again.
                field.textChanged.connect(lambda _text, key=role: self.reviewed[key].setChecked(False))
                row.addWidget(checked)
            layout.addLayout(row)
            self.sources[role] = field

        self.status = QLabel(
            'Select genuine recordings and explicitly mark only auditioned, '
            'independently recorded or reviewed separated stems.'
        )
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        save_row = QHBoxLayout()
        self.save_button = QPushButton('Save new song checkpoint')
        self.save_button.clicked.connect(self.save_checkpoint)
        self.brief_button = QPushButton('Webbie: read-only production summary')
        self.brief_button.clicked.connect(self.show_webbie_status)
        save_row.addWidget(self.save_button)
        save_row.addWidget(self.brief_button)
        layout.addLayout(save_row)

        transfer_row = QHBoxLayout()
        self.ai_take_button = QPushButton('Use selected Studio AI song take')
        self.ai_take_button.clicked.connect(self.import_ai_take)
        self.ai_separator_button = QPushButton('Send reference to AI separator')
        self.ai_separator_button.clicked.connect(self.prepare_separation)
        for button in (self.ai_take_button, self.ai_separator_button):
            transfer_row.addWidget(button)
        layout.addLayout(transfer_row)

        handoff_row = QHBoxLayout()
        self.mixer_send_button = QPushButton('Send reviewed stems to Band Mixer')
        self.mixer_send_button.clicked.connect(self.prepare_mixer)
        self.mix_import_button = QPushButton('Use last Band Mixer WAV')
        self.mix_import_button.clicked.connect(self.import_mix)
        self.release_send_button = QPushButton('Send finished WAV to Release Desk')
        self.release_send_button.clicked.connect(self.prepare_release)
        for button in (self.mixer_send_button, self.mix_import_button,
                       self.release_send_button):
            handoff_row.addWidget(button)
        layout.addLayout(handoff_row)
        review_row = QHBoxLayout()
        self.daw_button = QPushButton('Prepare reviewed stems for DAW')
        self.daw_button.clicked.connect(self.prepare_daw)
        self.qc_button = QPushButton('Inspect recordings in Audio Quality')
        self.qc_button.clicked.connect(self.open_quality)
        review_row.addWidget(self.daw_button)
        review_row.addWidget(self.qc_button)
        layout.addLayout(review_row)
        layout.addStretch()
        self.refresh_sessions()

    def choose_wav(self, role):
        chosen, _ = QFileDialog.getOpenFileName(
            self, 'Select ' + LABELS[role], str(Path.home()), 'PCM WAV (*.wav)',
        )
        if chosen:
            self.sources[role].setText(chosen)
            if role in self.reviewed:
                # Every file replacement needs a fresh explicit audition/approval.
                self.reviewed[role].setChecked(False)

    def start_fresh(self):
        self.session_id = None
        self.song_title.setText('Untitled song')
        self.notes.clear()
        for field in self.sources.values():
            field.clear()
        for checkbox in self.reviewed.values():
            checkbox.setChecked(False)
        self.status.setText('Fresh unsaved song. Save a new checkpoint when ready.')

    def data(self):
        paths = {role: field.text().strip()
                 for role, field in self.sources.items() if field.text().strip()}
        flags = {role: box.isChecked() for role, box in self.reviewed.items()}
        return paths, flags

    def save_checkpoint(self):
        paths, flags = self.data()
        title, notes = self.song_title.text(), self.notes.toPlainText()
        try:
            if self.session_id is None:
                self.session_id = create_session(title, notes=notes)
            filename = save_revision(
                self.session_id, title, paths, flags, notes=notes,
            )
            self.refresh_sessions()
            index = self.session_list.findData(self.session_id)
            if index >= 0:
                self.session_list.setCurrentIndex(index)
            self.status.setText(
                'New immutable checkpoint saved: ' + str(filename) +
                '. Previous song revisions remain intact.'
            )
        except (ProductionError, OSError, MixError) as exc:
            self.status.setText(str(exc))

    def refresh_sessions(self):
        chosen = self.session_id or self.session_list.currentData()
        self.session_list.clear()
        try:
            for session in list_sessions():
                self.session_list.addItem(session['title'], session['id'])
        except (ProductionError, OSError) as exc:
            self.status.setText('Could not read production sessions: ' + str(exc))
        if chosen:
            index = self.session_list.findData(chosen)
            if index >= 0:
                self.session_list.setCurrentIndex(index)

    def load_selected(self):
        chosen = self.session_list.currentData()
        if not chosen:
            self.status.setText('No song checkpoint has been saved yet.')
            return
        try:
            data = load_session(chosen)
        except (ProductionError, OSError, MixError) as exc:
            self.status.setText(str(exc))
            return
        self.session_id = chosen
        self.song_title.setText(data['title'])
        self.notes.setPlainText(data['notes'])
        for role in ROLES:
            self.sources[role].setText(data['assets'].get(role, ''))
            if role in self.reviewed:
                self.reviewed[role].setChecked(data['reviewed_stems'].get(role, False))
        missing = ', '.join(data['missing'])
        self.status.setText(
            'Checkpoint restored. Missing WAV files: ' + missing
            if missing else 'Checkpoint restored. ' + next_action(data)
        )

    def show_webbie_status(self):
        try:
            self.status.setText(latest_status())
        except (ProductionError, OSError):
            self.status.setText('Webbie production status unavailable; check local session storage.')

    def import_ai_take(self):
        if self.ai_panel is None:
            self.status.setText('Studio AI is not available.')
            return
        source = self.ai_panel.selected()
        if not source:
            self.status.setText('Select a generated song take in Studio AI first.')
            return
        try:
            path = valid_wav(source, 'AI full-song reference')
        except (MixError, OSError) as exc:
            self.status.setText(str(exc))
            return
        self.sources['reference_mix'].setText(str(path))
        self.status.setText(
            'AI song saved as a reference. This does not supply separate '
            'guitar, bass, drum or vocal stems. Save a checkpoint to remember it.'
        )

    def prepare_separation(self):
        if self.ai_panel is None:
            self.status.setText('Studio AI separator is unavailable.')
            return
        try:
            path = valid_wav(self.sources['reference_mix'].text().strip(), 'AI reference')
        except (MixError, OSError) as exc:
            self.status.setText(str(exc))
            return
        if self.ai_panel.separation_worker is not None:
            self.status.setText('Separator is busy. No changes applied.')
            return
        self.ai_panel.separation_source.setText(str(path))
        if self.tool_tabs is not None:
            self.tool_tabs.setCurrentIndex(0)
        self.status.setText('Reference selected in Studio AI. Click Separate there if approved.')

    def prepare_mixer(self):
        if self.band_mixer is None:
            self.status.setText('Band Mixer is unavailable.')
            return
        if self.band_mixer.worker is not None:
            self.status.setText('Band Mixer is rendering. No changes applied.')
            return
        paths, flags = self.data()
        chosen = {}
        try:
            for role in STEM_ROLES:
                if flags[role] and role in paths:
                    chosen[role] = valid_wav(paths[role], role)
            if len(chosen) < 2:
                raise ProductionError('Review at least two different independent WAV stems.')
            identities = {(p.stat().st_dev, p.stat().st_ino) for p in chosen.values()}
            if len(identities) != len(chosen):
                raise ProductionError('Selected stems must be different recorded WAVs.')
        except (ProductionError, MixError, OSError) as exc:
            self.status.setText(str(exc))
            return
        answer = QMessageBox.question(
            self, 'Replace Band Mixer source selections?',
            'Replace the currently selected Band Mixer input paths with '
            f'{len(chosen)} owner-reviewed WAV stems? Levels, pan and timing controls '
            'will remain untouched. Rendering will NOT start.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            self.status.setText('Band Mixer handoff cancelled.')
            return
        for role, field in self.band_mixer.track_fields.items():
            field.setText(str(chosen[role]) if role in chosen else '')
        if self.tool_tabs is not None:
            self.tool_tabs.setCurrentIndex(1)
        self.status.setText('Reviewed inputs transferred. Confirm mixer settings and render manually.')

    def import_mix(self):
        if self.band_mixer is None or not self.band_mixer.last_mix:
            self.status.setText('Render a Band Mixer WAV first.')
            return
        try:
            path = valid_wav(self.band_mixer.last_mix, 'finished mix')
        except (MixError, OSError) as exc:
            self.status.setText(str(exc))
            return
        self.sources['final_mix'].setText(str(path))
        self.status.setText('Finished mix selected. Audition it and save a checkpoint.')

    def prepare_release(self):
        if self.release_panel is None:
            self.status.setText('Release Desk is unavailable.')
            return
        if self.release_panel.worker is not None:
            self.status.setText('Release Desk is busy. No changes applied.')
            return
        try:
            path = valid_wav(self.sources['final_mix'].text().strip(), 'finished mix')
        except (MixError, OSError) as exc:
            self.status.setText(str(exc))
            return
        self.release_panel.source.setText(str(path))
        if self.tool_tabs is not None:
            self.tool_tabs.setCurrentIndex(2)
        self.status.setText('Final WAV selected in Release Desk. Export only after listening.')


    def prepare_daw(self):
        """Seed the existing WAV copy dialog, never start a copy silently."""
        paths, approvals = self.data()
        entries = []
        identities = set()
        daws = {
            'backing': 'instrumental_bed', 'lead_vocal': 'lead_vocal',
            'guest_vocal': 'backing_vocal', 'rhythm_guitar': 'rhythm_guitar',
            'lead_guitar': 'lead_guitar', 'bass': 'bass', 'drums': 'drums',
            'keys': 'piano_keys',
        }
        try:
            for role in STEM_ROLES:
                if role not in paths or not approvals[role]:
                    continue
                source = valid_wav(paths[role], role)
                identity = (source.stat().st_dev, source.stat().st_ino)
                if identity in identities:
                    raise ProductionError('Duplicate audio cannot be exported as separate stems.')
                identities.add(identity)
                entries.append({
                    'path': str(source), 'role': daws[role],
                    'label': role.replace('_', ' ').title(),
                })
            if not entries:
                raise ProductionError('Review at least one real independent WAV for DAW export.')
            if 'reference_mix' in paths:
                reference = valid_wav(paths['reference_mix'], 'song reference')
                identity = (reference.stat().st_dev, reference.stat().st_ino)
                if identity not in identities:
                    entries.append({'path': str(reference), 'role': 'reference_mix',
                                    'label': 'Whole-song reference, NOT a separate instrument'})
        except (ProductionError, OSError, MixError) as exc:
            self.status.setText(str(exc))
            return
        dialog = MultitrackDialog(entries, title=self.song_title.text(), parent=self)
        self.status.setText(
            'DAW editor opened with reviewed stems. Tracks start at zero; '
            'listen and align manually. Export only if you approve.'
        )
        dialog.exec_()

    def open_quality(self):
        if self.quality_panel is None or self.tool_tabs is None:
            self.status.setText('Audio Quality tab is unavailable.')
            return
        if self.quality_panel.worker is not None:
            self.status.setText('Audio Quality is already analyzing. No changes applied.')
            return
        self.quality_panel.import_board()
        self.tool_tabs.setCurrentWidget(self.quality_panel.parentWidget())
        self.status.setText('Audio Quality opened with selected WAVs; click Inspect to run.')
