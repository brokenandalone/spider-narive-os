"""Webbie computer-control surface, explicitly opened and approved by the owner.

Source-only. No autonomous LLM action or microphone adapter is connected yet.
The dialog uses the existing installed XDG menu and restricted X11 driver.
The user personally grants a limited task and can revoke it any time.
"""
from pathlib import Path
import sys
import os

from PyQt5.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QSpinBox, QTextEdit, QVBoxLayout, QScrollArea,
                             QWidget)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'webbie/actions'))
from desktop_control import app_catalog, KEYS
from window_safety import ConfinedDesktopOperator
from task_grants import TaskGrant
sys.path.insert(0, str(ROOT / 'webbie/agent'))
from stop_signal import consume_stop
from browser_routes import canonical_url, is_browser_app
from screen_capture import capture_window, describe_window
sys.path.insert(0, str(ROOT / 'webbie/brain'))
from local_models import choose_local_model
from visual_step import propose_step
from autopilot_policy import AutopilotPolicy
from navigation_missions import NavigationMission, parse_navigation_request
from action_journal import ActionJournal
from webbie_operator_bridge import OperatorBridge


def parse_open_request(message, apps):
    """Offer UI control only for a specifically installed desktop app.

    The command text does not itself grant permissions. Other instructions
    remain in Webbie's normal conversation handler.
    """
    import re
    phrase = re.sub(r'\s+', ' ', str(message).strip())
    match = re.fullmatch(
        r'(?:hey\s+)?(?:webbie|webby|web)[, ]+\s*(?:open|launch|start)\s+(.+?)'
        r'|(?:open|launch|start)\s+(.+?)', phrase, flags=re.I)
    if not match:
        return None
    name = (match.group(1) or match.group(2) or '').strip(' ,.!?')
    candidates = [app for app in apps if
                  app.name.casefold() == name.casefold() or
                  app.desktop_id.casefold().removesuffix('.desktop') == name.casefold()]
    return candidates[0] if len(candidates) == 1 else None


class ScreenWorker(QThread):
    described = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, jpeg, model, parent=None):
        super().__init__(parent)
        self.jpeg = jpeg
        self.model = model

    def run(self):
        try:
            self.described.emit(describe_window(
                self.jpeg, 'Briefly identify the visible application controls. '
                'Do not repeat personal or secret data.',
                model=self.model or choose_local_model('vision')))
        except (ValueError, RuntimeError, OSError) as error:
            self.failed.emit(str(error))
        finally:
            self.jpeg = None


class StepWorker(QThread):
    proposed = pyqtSignal(object)
    failed = pyqtSignal(str)
    def __init__(self, jpeg, task, width, height, model, parent=None):
        super().__init__(parent)
        self.jpeg = jpeg
        self.model = model
        self.task = task
        self.width = width
        self.height = height
    def run(self):
        try:
            self.proposed.emit(
                propose_step(self.jpeg, self.task, self.width, self.height,
                             model=self.model or choose_local_model('vision')))
        except (ValueError, RuntimeError, OSError) as error:
            self.failed.emit(str(error))
        finally:
            self.jpeg = None


class WebbieComputerDialog(QDialog):
    taskApproved = pyqtSignal(str)
    screenObserved = pyqtSignal(str)
    authorizationRevoked = pyqtSignal()

    def __init__(self, parent=None, *, discover=None, run=None, launcher=None,
                 browser_opener=None):
        super().__init__(parent)
        self.setWindowTitle('WEBBIE | COMPUTER CONTROL')
        self.setObjectName('webbieComputerControl')
        self.resize(640, 730)
        self.apps = list(discover() if discover else app_catalog().discover_apps())
        # Resolve preferences against locally INSTALLED Ollama models in the
        # background worker. Never download or switch the owner's engine.
        self.vision_model = None
        self.browser_opener = browser_opener or QDesktopServices.openUrl
        self.grant = TaskGrant(approve_sensitive=self.approve_sensitive)
        self.operator = ConfinedDesktopOperator(
            permission=self.grant.authorize,
            discover=lambda: self.apps,
            runner=run, launcher=launcher)
        self.screen_worker = None
        self.step_worker = None
        self.autopilot = AutopilotPolicy()
        self.autopilot_revision = 0
        self.nav_mission = NavigationMission()
        self.action_journal = ActionJournal()
        self.pending_step = None
        self.pending_step_target = None
        self.bridge = OperatorBridge(grant=self.grant, parent=self)
        self.bridge.openRequested.connect(self.handle_voice_open)
        self.bridge.webRequested.connect(self.handle_voice_web)
        self.bridge.navigationProposed.connect(self.handle_voice_navigation)

        # Keep all explicit approval controls readable on smaller screens.
        outer = QVBoxLayout(self)
        self.controls_scroll = QScrollArea(self)
        self.controls_scroll.setObjectName('webbieControlsScrollable')
        self.controls_scroll.setWidgetResizable(True)
        body = QWidget(self.controls_scroll)
        self.controls_scroll.setWidget(body)
        outer.addWidget(self.controls_scroll)
        layout = QVBoxLayout(body)
        notice = QLabel(
            'CONTROL IS OFF BY DEFAULT. Choose an installed program and a '
            'specific task. Permission lasts up to five minutes or 75 actions, '
            'whichever comes first. Webbie cannot change system settings '
            'or run arbitrary shell commands through this tool.')
        notice.setWordWrap(True); layout.addWidget(notice)
        form = QFormLayout(); layout.addLayout(form)
        self.app_select = QComboBox()
        self.app_select.setObjectName('webbieInstalledProgram')
        self.app_select.currentIndexChanged.connect(lambda _=None: self.pause_autopilot())
        for app in self.apps:
            self.app_select.addItem(f'{app.name}  [{app.workspace}]', app.desktop_id)
        form.addRow('Installed program', self.app_select)
        self.task = QLineEdit()
        self.task.setPlaceholderText('Example: help edit the current guitar recording')
        form.addRow('Approved task', self.task)

        auth_row = QHBoxLayout(); layout.addLayout(auth_row)
        self.grant_button = QPushButton('Authorize this task')
        self.grant_button.clicked.connect(self.authorize)
        auth_row.addWidget(self.grant_button)
        self.stop_button = QPushButton('STOP WEBBIE')
        self.stop_button.setObjectName('webbieEmergencyStop')
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setStyleSheet('background:#6e1e55; color:white; font-weight:bold')
        auth_row.addWidget(self.stop_button)
        self.state = QLabel('OFF | Webbie cannot operate applications')
        self.state.setWordWrap(True)
        layout.addWidget(self.state)

        app_row = QHBoxLayout(); layout.addLayout(app_row)
        self.open_button = QPushButton('Open selected program')
        self.open_button.clicked.connect(self.open_app); app_row.addWidget(self.open_button)
        self.browser_url = QLineEdit()
        self.browser_url.setPlaceholderText('HTTPS website, e.g. github.com')
        self.browser_url.setObjectName('webbieBrowserAddress')
        layout.addWidget(self.browser_url)
        self.open_web_button = QPushButton('Open approved website')
        self.open_web_button.setObjectName('webbieOpenWebsite')
        self.open_web_button.clicked.connect(self.open_website)
        layout.addWidget(self.open_web_button)
        self.refresh_button = QPushButton('Find open windows')
        self.refresh_button.clicked.connect(self.refresh_windows); app_row.addWidget(self.refresh_button)

        self.windows = QComboBox(); self.windows.setObjectName('webbieWindowSelector')
        self.windows.currentIndexChanged.connect(lambda _=None: self.pause_autopilot())
        layout.addWidget(self.windows)
        self.bind_button = QPushButton('Authorize selected window')
        self.bind_button.clicked.connect(self.bind_window)
        layout.addWidget(self.bind_button)
        window_row = QHBoxLayout(); layout.addLayout(window_row)
        self.focus_button = QPushButton('Focus window')
        self.focus_button.clicked.connect(self.focus_window); window_row.addWidget(self.focus_button)
        self.inspect_button = QPushButton('Inspect window once')
        self.inspect_button.clicked.connect(self.inspect_window); window_row.addWidget(self.inspect_button)
        self.close_button = QPushButton('Close window')
        self.close_button.clicked.connect(self.close_window); window_row.addWidget(self.close_button)

        row = QHBoxLayout(); layout.addLayout(row)
        self.click_x = QSpinBox(); self.click_x.setRange(0, 16384); self.click_x.setPrefix('X ')
        self.click_y = QSpinBox(); self.click_y.setRange(0, 16384); self.click_y.setPrefix('Y ')
        self.click_button = QPushButton('Click at coordinates')
        self.click_button.clicked.connect(self.click)
        row.addWidget(self.click_x); row.addWidget(self.click_y); row.addWidget(self.click_button)
        row2 = QHBoxLayout(); layout.addLayout(row2)
        self.key = QComboBox()
        self.key.addItems(sorted(KEYS))
        self.key_button = QPushButton('Press selected key')
        self.key_button.clicked.connect(self.press)
        row2.addWidget(self.key, 1); row2.addWidget(self.key_button)
        row3 = QHBoxLayout(); layout.addLayout(row3)
        self.to_type = QLineEdit(); self.to_type.setPlaceholderText('Text to type in the focused program')
        self.type_button = QPushButton('Type')
        self.type_button.clicked.connect(self.type_text)
        row3.addWidget(self.to_type, 1); row3.addWidget(self.type_button)
        planning = QHBoxLayout(); layout.addLayout(planning)
        self.suggest_button = QPushButton('Webbie: suggest next safe step')
        self.suggest_button.clicked.connect(self.suggest_step)
        planning.addWidget(self.suggest_button)
        self.apply_step_button = QPushButton('Apply reviewed step')
        self.apply_step_button.clicked.connect(self.apply_step)
        planning.addWidget(self.apply_step_button)
        autopilot_row = QHBoxLayout(); layout.addLayout(autopilot_row)
        self.autopilot_start = QPushButton('Start supervised Autopilot')
        self.autopilot_start.setObjectName('webbieAutopilotStart')
        self.autopilot_start.clicked.connect(self.begin_autopilot)
        autopilot_row.addWidget(self.autopilot_start)
        self.autopilot_pause = QPushButton('Pause Autopilot')
        self.autopilot_pause.setObjectName('webbieAutopilotPause')
        self.autopilot_pause.clicked.connect(self.pause_autopilot)
        autopilot_row.addWidget(self.autopilot_pause)
        mission_label = QLabel(
            'Jarvis navigation missions: preview a literal request, then '
            'approve each step in one specifically authorized window.')
        mission_label.setWordWrap(True)
        layout.addWidget(mission_label)
        self.navigation_input = QLineEdit()
        self.navigation_input.setObjectName('webbieNavigationRequest')
        self.navigation_input.setMaxLength(220)
        self.navigation_input.setPlaceholderText(
            'scroll down twice then go back, or next tab')
        layout.addWidget(self.navigation_input)
        navigation_row = QHBoxLayout(); layout.addLayout(navigation_row)
        self.nav_preview_button = QPushButton('Preview navigation steps')
        self.nav_preview_button.setObjectName('webbieNavPreview')
        self.nav_preview_button.clicked.connect(self.preview_navigation)
        navigation_row.addWidget(self.nav_preview_button)
        self.nav_next_button = QPushButton('Run next reviewed step')
        self.nav_next_button.setObjectName('webbieNavNext')
        self.nav_next_button.clicked.connect(self.run_navigation_step)
        navigation_row.addWidget(self.nav_next_button)
        self.nav_cancel_button = QPushButton('Cancel mission')
        self.nav_cancel_button.clicked.connect(self.cancel_navigation)
        navigation_row.addWidget(self.nav_cancel_button)
        self.nav_status = QLabel('No navigation mission active.')
        self.nav_status.setWordWrap(True)
        layout.addWidget(self.nav_status)
        self.report = QTextEdit(); self.report.setReadOnly(True)
        self.report.setMaximumHeight(150); layout.addWidget(self.report)
        self.report.setPlainText('No program or screen is being controlled.')
        self.activity = QTextEdit(); self.activity.setReadOnly(True)
        self.activity.setObjectName('webbieActivityHistory')
        self.activity.setMaximumHeight(135)
        self.activity.setPlainText(self.action_journal.display())
        self.activity.setAccessibleName('Recent Webbie computer actions')
        layout.addWidget(QLabel('Recent computer actions (current session only)'))
        layout.addWidget(self.activity)
        clear_history = QPushButton('Clear action history')
        clear_history.clicked.connect(self.clear_activity)
        layout.addWidget(clear_history)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(1000)
        self.refresh_status()

    def status(self, message):
        self.report.setPlainText(message)

    def record_activity(self, event):
        self.action_journal.record(event)
        self.activity.setPlainText(self.action_journal.display())

    def clear_activity(self):
        self.action_journal.clear()
        self.activity.setPlainText(self.action_journal.display())

    def selected_app(self):
        identity = self.app_select.currentData()
        return next((app for app in self.apps if app.desktop_id == identity), None)

    def offer_program(self, app_id):
        for n in range(self.app_select.count()):
            if self.app_select.itemData(n) == app_id:
                self.app_select.setCurrentIndex(n)
                return True
        return False

    def authorize(self):
        app = self.selected_app()
        task = self.task.text().strip()
        if app is None or not task:
            self.status('Select an installed application and describe the task.')
            return
        choice = QMessageBox.question(
            self, 'Authorize Webbie computer control?',
            f'Allow Webbie to work in {app.name} for this task?\n\n'
            f'{task[:300]}\n\n'
            'Expires after five minutes or 75 actions. You can press STOP '
            'at any moment. Program changes can affect your files; review '
            'each change. Do not grant a task that requires passwords.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if choice != QMessageBox.Yes:
            return
        # Clear a stale stop-only signal before accepting this NEW on-screen grant.
        consume_stop()
        self.pause_autopilot()
        self.pending_step = None
        self.grant.activate(task, app.desktop_id, seconds=300)
        self.operator.begin_new_task()
        try:
            self.bridge.activate()
        except (OSError, RuntimeError, ValueError, PermissionError) as error:
            self.operator.stop()
            self.grant.stop()
            self.status('Desktop voice bridge unavailable: ' + str(error))
            return
        self.record_activity('grant_started')
        self.taskApproved.emit(task)
        self.status(f'Authorized: {app.name}. No changes made yet.')
        self.refresh_status()

    def stop(self):
        self.autopilot.stop()
        self.nav_mission.stop()
        self.record_activity('stopped')
        self.operator.stop()
        self.pending_step = None
        self.pending_step_target = None
        self.grant.stop()
        self.bridge.deactivate()
        self.authorizationRevoked.emit()
        self.status('STOPPED. No additional Webbie computer actions are authorized.')
        self.refresh_status()

    def approve_sensitive(self, action, preview):
        if action == 'browser.open.confirm':
            title = 'Confirm website navigation'
            body = (preview + '\n\nOpening a site may share network data with '
                    'that site. Proceed in your system default browser?')
        else:
            title = 'Confirm Webbie change'
            body = preview + '\n\nConfirm this potentially destructive computer action?'
        approved = (QMessageBox.question(
            self, title, body,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes)
        self.record_activity('review_approved' if approved else 'review_denied')
        return approved

    def refresh_status(self):
        # A deliberate voice/GUI "Webby stop" revokes desktop task grants.
        # Consume only a stop-only marker, never instructions or approvals.
        if consume_stop():
            self.stop()
            return
        data = self.grant.status()
        active = data['active']
        if not active and self.autopilot.active:
            self.autopilot.stop()
        self.state.setText(
            (f"AUTHORIZED | {data['remaining_seconds']} sec left | "
             f"{data['remaining_actions']} actions | {data['task']}")
            if active else 'OFF | Webbie cannot operate applications')
        self.autopilot_start.setEnabled(active and not self.autopilot.active)
        self.autopilot_pause.setEnabled(self.autopilot.active)
        self.open_web_button.setEnabled(active and is_browser_app(self.selected_app())
                                        if self.selected_app() is not None else False)
        for control in (self.open_button, self.refresh_button, self.bind_button, self.focus_button,
                        self.inspect_button, self.close_button, self.click_button,
                        self.key_button, self.type_button, self.suggest_button):
            control.setEnabled(active)
        self.nav_preview_button.setEnabled(active)
        self.nav_next_button.setEnabled(active and
                                        self.nav_mission.plan is not None and
                                        self.nav_mission.clock() < self.nav_mission.expires)
        self.apply_step_button.setEnabled(
            active and self.pending_step is not None and
            self.pending_step.get('action') in {'click', 'press'})
        if not active:
            self.nav_mission.stop()
            self.nav_status.setText('No active grant; navigation mission stopped.')
            self.pending_step = None
            self.bridge.deactivate()
            if not self.operator.cancelled.is_set():
                self.operator.stop()

    def action(self, method, *args):
        try:
            outcome = method(*args)
        except (ValueError, RuntimeError, PermissionError, InterruptedError, OSError) as error:
            self.status(str(error))
            return None
        self.status(str(outcome))
        self.refresh_status()
        return outcome

    def handle_voice_open(self, app_id):
        # A socket request cannot create/extend approval; the selected app ID
        # and current GUI grant are rechecked before even attempting a launch.
        result = None
        app = self.selected_app()
        if (app is not None and app.desktop_id == app_id
                and self.grant.status()['active']):
            result = self.action(self.operator.open_app, app.name)
        peer = self.bridge.pending
        if peer is not None:
            self.bridge.finish(
                peer, f'Launch requested for {app.name}.' if result else
                'App launch denied or unsuccessful. Check the desktop panel.')

    def offer_site(self, url):
        """Fill a proposal visibly; only the user can grant browser control."""
        try:
            candidate = canonical_url(url)
        except ValueError:
            self.status('Only public HTTPS website addresses are supported.')
            return False
        browser_indices = [
            number for number, app in enumerate(self.apps) if is_browser_app(app)]
        if not browser_indices:
            self.status('No installed WebBrowser application is available.')
            return False
        current = self.selected_app()
        if current is None or not is_browser_app(current):
            desired_id = self.apps[browser_indices[0]].desktop_id
            for index in range(self.app_select.count()):
                if self.app_select.itemData(index) == desired_id:
                    self.app_select.setCurrentIndex(index)
                    break
        self.browser_url.setText(candidate)
        if not self.task.text().strip():
            self.task.setText('Open a reviewed website in my browser')
        self.status('Review the URL and authorize this browser task before opening.')
        return True

    def open_website(self, url=None):
        """Owner-confirmed website navigation; never starts a privileged command."""
        app = self.selected_app()
        status = self.grant.status()
        if (app is None or not is_browser_app(app) or not status['active']
                or status['selected_app_id'] != app.desktop_id
                or self.operator.cancelled.is_set()):
            self.status('Select a web browser and authorize the current task first.')
            return False
        try:
            destination = canonical_url(
                self.browser_url.text() if url is None else url)
        except ValueError as error:
            self.status(str(error))
            return False
        # Show the exact destination before user confirmation.
        self.browser_url.setText(destination)
        if not self.grant.authorize(
                'browser.open.confirm', 'Website: ' + destination):
            self.status('Website navigation not approved.')
            return False
        if not self.grant.status()['active'] or self.operator.cancelled.is_set():
            self.status('Browser grant expired before navigation.')
            return False
        if not self.browser_opener(QUrl(destination)):
            self.status('The system default browser could not handle this link.')
            return False
        self.browser_url.setText(destination)
        self.record_activity('website_requested')
        self.status('Website open requested in the system default browser: ' +
                    destination[:300])
        self.refresh_status()
        return True

    def handle_voice_web(self, url):
        opened = self.open_website(url)
        if self.bridge.pending is not None:
            self.bridge.finish(
                self.bridge.pending,
                'Website navigation requested in your default browser.' if opened
                else 'Website not opened. Review the Computer Control panel.')

    def open_app(self):
        app = self.selected_app()
        if app:
            result = self.action(self.operator.open_app, app.name)
            self.record_activity('app_requested' if result else 'app_denied')

    def refresh_windows(self):
        listing = self.action(self.operator.windows)
        if listing is None:
            return
        self.windows.clear()
        for item in listing:
            self.windows.addItem(item['title'] or item['id'], item['id'])
        self.status(f'Found {len(listing)} windows. Select the target you want to operate.')

    def selected_window(self):
        return self.windows.currentData()

    def bind_window(self):
        target = self.selected_window()
        if not target:
            self.status('Choose an open window first.'); return
        chosen = self.windows.currentText()
        choice = QMessageBox.question(
            self, 'Authorize this program window?',
            f'Allow Webbie to operate this exact window?\n\n{chosen[:200]}\n\n'
            'The currently selected application is not automatically proof of '
            'the window owner. Verify its title and contents yourself.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if choice == QMessageBox.Yes:
            self.pause_autopilot()
            if self.action(self.operator.bind_window, target):
                self.record_activity('window_bound')

    def focus_window(self):
        if self.selected_window():
            self.action(self.operator.focus, self.selected_window())

    def click(self):
        # The owner chooses exact coordinates. Autonomous pointer movement from
        # LLM-derived screen contents is intentionally NOT connected yet.
        self.action(self.operator.click, self.click_x.value(), self.click_y.value())

    def press(self):
        self.action(self.operator.press, self.key.currentText())

    def type_text(self):
        if self.to_type.text():
            self.action(self.operator.type_text, self.to_type.text())
            self.to_type.clear()

    def close_window(self):
        if self.selected_window():
            self.action(self.operator.close_window, self.selected_window())

    def _publish_screen_observation(self, message):
        # A delayed local vision result after STOP must not restore awareness.
        if (self.grant.status()['active'] and
                self.operator.target_window == self.selected_window()):
            self.screenObserved.emit(message)

    def inspect_window(self):
        target = self.selected_window()
        if (not target or target != self.operator.target_window or
                not self.grant.status()['active']):
            self.status('Authorize the exact window before inspecting it.'); return
        if self.screen_worker and self.screen_worker.isRunning():
            self.status('Current window inspection is still running.')
            return
        choice = QMessageBox.question(
            self, 'Share this window with LOCAL Webbie?',
            'Take one screenshot of this selected application window and send '
            'it only to the local Ollama vision model? It may contain private '
            'information. Do not inspect password or financial windows.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if choice != QMessageBox.Yes:
            return
        try:
            # Permission covers observation but NEVER retains this image.
            if not self.grant.authorize('observe.windows', 'Inspect selected window'):
                raise PermissionError('Task authorization expired')
            if target not in {item['id'] for item in self.operator.windows()}:
                raise ValueError('The selected window no longer exists')
            image = capture_window(target, approved=True)
            self.record_activity('window_observed')
        except (ValueError, RuntimeError, PermissionError, OSError) as error:
            self.status(str(error)); return
        self.status('Local Ollama is describing this one authorized window.')
        self.screen_worker = ScreenWorker(image, self.vision_model, self)
        self.screen_worker.described.connect(
            lambda message: self.status('Local screen observation (untrusted):\n' + message))
        self.screen_worker.described.connect(self._publish_screen_observation)
        self.screen_worker.failed.connect(self.status)
        self.screen_worker.start()

    def pause_autopilot(self):
        self.nav_mission.stop()
        if self.autopilot.active:
            self.autopilot.stop()
            self.status('Autopilot paused. Existing task grant remains revocable.')
        self.pending_step = None
        if hasattr(self, 'autopilot_pause'):
            self.refresh_status()

    def begin_autopilot(self):
        """One explicit grant for multiple fresh screen observations in one window."""
        data = self.grant.status()
        window = self.selected_window()
        if (not data['active'] or not window or
                window != self.operator.target_window):
            self.status('Authorize the task and its exact window first.')
            return
        if (self.step_worker and self.step_worker.isRunning()):
            self.status('A screen inspection is already running.')
            return
        if (QMessageBox.question(
                self, 'Start supervised Webbie Autopilot?',
                'Webbie may take up to SIX fresh snapshots of this exact window '
                'and use local Ollama to navigate with simple keys. '
                'Every click still requires your approval. '
                'Autopilot stops after two minutes, six actions, uncertainty, '
                'repeated steps, or STOP. No passwords, messages, purchases, '
                'deletions or admin tasks. '
                'The window must not contain sensitive information. '
                'Do you authorize this limited task?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes):
            return
        try:
            self.autopilot_revision = self.autopilot.begin(
                data['task'], window, approved=True)
        except (ValueError, PermissionError) as error:
            self.status(str(error)); return
        self.pending_step = None
        self.status('Autopilot started for one authorized window and task.')
        self.refresh_status()
        QTimer.singleShot(0, lambda: self._autopilot_next(self.autopilot_revision))

    def _autopilot_ready(self, revision, window):
        return self.autopilot.ready(
            window=window,
            granted=self.grant.status()['active'] and
                    window == self.operator.target_window and
                    window == self.selected_window(),
            revision=revision)

    def _autopilot_next(self, revision):
        window = self.operator.target_window
        if not self._autopilot_ready(revision, window):
            self.autopilot.stop()
            self.status('Autopilot paused because approval expired or the window changed.')
            self.refresh_status()
            return
        if self.step_worker and self.step_worker.isRunning():
            QTimer.singleShot(200, lambda: self._autopilot_next(revision))
            return
        try:
            if window not in {item['id'] for item in self.operator.windows()}:
                raise RuntimeError('Authorized window is no longer open')
            jpeg = capture_window(window, approved=True)
            qimage = QImage.fromData(jpeg, 'JPEG')
            if qimage.isNull():
                raise RuntimeError('Could not inspect the authorized window')
        except (OSError, ValueError, RuntimeError, PermissionError, InterruptedError) as error:
            self.autopilot.stop()
            self.status('Autopilot paused: ' + str(error))
            self.refresh_status()
            return
        self.step_worker = StepWorker(
            jpeg, self.autopilot.task, qimage.width(), qimage.height(),
            self.vision_model, self)
        self.step_worker.proposed.connect(
            lambda plan, token=revision, target=window:
            self._autopilot_proposed(plan, token, target))
        self.step_worker.failed.connect(
            lambda message, token=revision: self._autopilot_failed(message, token))
        self.step_worker.start()
        self.status('Autopilot examining fresh window image. STOP is available.')

    def _autopilot_failed(self, message, revision):
        if revision != self.autopilot.revision:
            return
        self.autopilot.stop()
        self.status('Autopilot paused: ' + message)
        self.refresh_status()

    def _autopilot_proposed(self, plan, revision, window):
        if not self._autopilot_ready(revision, window):
            self.status('Autopilot discarded a stale model suggestion.')
            return
        decision = self.autopilot.decide(
            plan, window=window, granted=True, revision=revision)
        if decision == 'done':
            self.status('Autopilot reported task complete. Please verify the screen.')
            self.refresh_status()
            return
        if decision == 'pause':
            self.status('Autopilot paused for uncertainty, risk or step limit: ' + str(plan))
            self.refresh_status()
            return
        if decision == 'review':
            self.pending_step = plan
            self.pending_step_target = window
            self.status('Autopilot needs click approval: ' + str(plan))
            self.refresh_status()
            return
        if decision == 'auto':
            result = self.action(self.operator.press, plan['key'])
            if result is None:
                self.autopilot.stop()
                self.status('Autopilot paused after unsuccessful navigation.')
                return
            more = self.autopilot.record_step(
                window=window, granted=self.grant.status()['active'],
                revision=revision)
            if more:
                QTimer.singleShot(200, lambda: self._autopilot_next(revision))
            else:
                self.status('Autopilot reached its step limit; screen review required.')
                self.refresh_status()

    def suggest_step(self):
        """Observe ONE approved window, then ask local AI for ONE safe proposal."""
        grant = self.grant.status()
        window_id = self.selected_window()
        if (not grant['active'] or not window_id or
                window_id != self.operator.target_window):
            self.status('Approve your task and bind the exact window first.')
            return
        if self.step_worker and self.step_worker.isRunning():
            self.status('Webbie is already inspecting the selected window.')
            return
        if (QMessageBox.question(
                self, 'Share one window frame?',
                'Send one snapshot of the authorized window to local Ollama '
                'to suggest a routine next step? No action will happen '
                'automatically. Avoid password, banking and private windows.',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes):
            return
        try:
            current = {w['id'] for w in self.operator.windows()}
            if window_id not in current:
                raise ValueError('Window closed or changed; select it again')
            image = capture_window(window_id, approved=True)
            qimage = QImage.fromData(image, 'JPEG')
            if qimage.isNull():
                raise RuntimeError('Cannot determine window screenshot dimensions')
        except (OSError, ValueError, RuntimeError, PermissionError) as error:
            self.status(str(error)); return
        self.pending_step = None
        self.pending_step_target = window_id
        self.step_worker = StepWorker(
            image, grant['task'], qimage.width(), qimage.height(),
            self.vision_model, self)
        self.step_worker.proposed.connect(self.step_proposed)
        self.step_worker.failed.connect(self.status)
        self.step_worker.start()
        self.status('Webbie is proposing one step from a fresh local screen snapshot.')
        self.refresh_status()

    def step_proposed(self, plan):
        if (not self.grant.status()['active'] or
                self.pending_step_target != self.operator.target_window):
            self.pending_step = None
            self.status('Task expired or target changed. Proposal discarded.')
            return
        self.pending_step = plan if plan.get('action') in ('click', 'press') else None
        self.status('Untrusted local AI suggestion: ' + str(plan) +
                    '\nNo action taken. Review the exact operation.')
        self.refresh_status()

    def apply_step(self):
        plan = self.pending_step
        self.pending_step = None
        self.refresh_status()
        if not plan or not self.grant.status()['active']:
            return
        if self.pending_step_target != self.operator.target_window:
            self.status('Target changed; proposal discarded.')
            return
        detail = (f"Click at ({plan['x']}, {plan['y']})" if plan['action']=='click'
                  else "Press " + plan['key'])
        if (QMessageBox.question(
                self, 'Review Webbie proposed action',
                f"{detail}\nReason: {plan['reason']}\n"
                'The model may be mistaken. Do this one step?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes):
            self.pause_autopilot()
            self.status('Suggested step rejected.'); return
        result = None
        if plan['action'] == 'click':
            result = self.action(self.operator.click, plan['x'], plan['y'])
        elif plan['action'] == 'press':
            result = self.action(self.operator.press, plan['key'])
        if self.autopilot.active:
            revision = self.autopilot_revision
            window = self.operator.target_window
            if result is not None and self.autopilot.record_step(
                    window=window, granted=self.grant.status()['active'],
                    revision=revision):
                QTimer.singleShot(200, lambda: self._autopilot_next(revision))
            else:
                self.autopilot.stop()
                self.status('Autopilot stopped after step limit or failed action.')
        else:
            self.status(self.report.toPlainText() +
                        '\nVerify the window before the next step.')
        self.refresh_status()

    def handle_voice_navigation(self, phrase):
        """Voice may propose, but only local clicks can authorize and execute."""
        staged = self.offer_navigation(phrase)
        if self.bridge.pending is not None:
            self.bridge.finish(
                self.bridge.pending,
                'Navigation staged. Review the steps in Computer Control.' if staged
                else 'Unable to stage that navigation request.')

    def offer_navigation(self, request):
        """Present only direct user-supplied navigation text; no auto-action."""
        proposed = parse_navigation_request(request)
        if proposed is None:
            return False
        self.nav_mission.stop()
        self.navigation_input.setText(str(request)[:220])
        self.nav_status.setText(
            f'{len(proposed.steps)} navigation step(s) proposed. '
            'Authorize a task, select and bind its exact window, then preview.')
        return True

    def preview_navigation(self):
        """No mouse or key movement occurs from a preview."""
        self.nav_mission.stop()
        task = parse_navigation_request(self.navigation_input.text())
        if task is None:
            self.nav_status.setText('Unsupported request. Use scroll, back, '
                                    'forward, reload, or next/previous tab.')
            self.refresh_status()
            return
        grant = self.grant.status()
        target = self.selected_window()
        app = self.selected_app()
        browser = app is not None and is_browser_app(app)
        if (not grant['active'] or target is None or
                target != self.operator.target_window or app is None):
            self.nav_status.setText(
                'First authorize a desktop task and bind the exact window.')
            self.refresh_status()
            return
        if grant['selected_app_id'] != app.desktop_id:
            self.nav_status.setText('Authorized app changed; please reauthorize.')
            self.refresh_status()
            return
        try:
            revision = self.nav_mission.stage(
                task, window=target, selected_app_id=app.desktop_id,
                browser=browser, approved=True)
        except (PermissionError, ValueError) as error:
            self.nav_status.setText(str(error))
            self.refresh_status()
            return
        lines = [f'{index + 1}. {step.label} ({step.key})'
                 for index, step in enumerate(task.steps)]
        self.record_activity('mission_staged')
        self.nav_status.setText(
            'Proposed sequence, NO ACTION TAKEN:\n' + '\n'.join(lines) +
            '\nApprove each step using Run next reviewed step. '
            f'This mission expires in two minutes (revision {revision}).')
        self.refresh_status()

    def run_navigation_step(self):
        """One clicked step, one checked grant, one bound-window operation."""
        app = self.selected_app()
        grant = self.grant.status()
        target = self.selected_window()
        browser = app is not None and is_browser_app(app)
        revision = self.nav_mission.revision
        try:
            step = self.nav_mission.next_step(
                granted=grant['active'] and
                        target == self.operator.target_window and
                        grant['selected_app_id'] == (
                            app.desktop_id if app else None),
                window=target, app_id=app.desktop_id if app else None,
                browser=browser, revision=revision)
        except (ValueError, PermissionError) as error:
            self.nav_status.setText(str(error))
            self.refresh_status()
            return
        # A user click is a new, per-step consent event; no model output
        # or socket command enters this action path.
        result = self.action(self.operator.press, step.key)
        pending = self.nav_mission.complete(
            success=result is not None, revision=revision)
        if result is None:
            self.record_activity('mission_failed')
            self.nav_status.setText('Navigation failed; remaining steps canceled.')
        elif pending:
            self.record_activity('mission_step')
            self.nav_status.setText('Step completed. ' + self.nav_mission.progress())
        else:
            self.record_activity('mission_done')
            self.nav_status.setText(
                'All requested navigation steps sent. Verify the window.')
        self.refresh_status()

    def cancel_navigation(self):
        self.nav_mission.stop()
        self.record_activity('mission_canceled')
        self.nav_status.setText('Navigation mission canceled.')
        self.refresh_status()

    def closeEvent(self, event):
        self.stop()
        if ((self.screen_worker and self.screen_worker.isRunning()) or
                (self.step_worker and self.step_worker.isRunning())):
            self.hide()
            event.ignore()
        else:
            event.accept()
