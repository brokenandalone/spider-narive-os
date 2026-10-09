"""Small notification popup driven by The Web's existing private journal."""
import json
from pathlib import Path
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton
from notification_center import load_state

def newest_event(path):
    path=Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>131072:return None
        lines=path.read_text(encoding='utf-8').splitlines()
        if not lines:return None
        data=json.loads(lines[-1])
        if not isinstance(data,dict):return None
        return {'app':str(data.get('app','Application'))[:60],
                'title':str(data.get('title',''))[:100],
                'message':str(data.get('message',''))[:240],
                'time':str(data.get('time',''))[:50]}
    except (OSError,ValueError,UnicodeError,TypeError):
        return None

class NotificationToast(QWidget):
    def __init__(self,parent=None,state_path=None):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
        self.state_path=Path(state_path) if state_path is not None else Path.home()/'.local/state/spider-os/notifications.json'
        self.journal=self.state_path.parent/'external-notifications.jsonl'
        self.last_key=None
        self.setWindowTitle('The Web Notification')
        self.setStyleSheet('QWidget{background:#241632;color:#f6eaff;border:1px solid #8147b7;border-radius:9px;} QLabel{border:0;}')
        layout=QVBoxLayout(self)
        self.title=QLabel()
        self.title.setTextFormat(Qt.PlainText)
        layout.addWidget(self.title)
        self.message=QLabel()
        # Notification content is supplied by other processes. Display as
        # literal text, never interpret HTML, links or rich-text markup.
        self.message.setTextFormat(Qt.PlainText)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        dismiss=QPushButton('Dismiss');dismiss.clicked.connect(self.hide);layout.addWidget(dismiss)
        self.setFixedWidth(330)
        self.poller=QTimer(self);self.poller.timeout.connect(self.refresh)
        self.poller.start(1200)
        self.dismiss_timer=QTimer(self);self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.hide)
        # Ignore existing history when the desktop launches.
        first=newest_event(self.journal)
        if first:self.last_key=(first['time'],first['title'],first['message'])

    def refresh(self):
        newest=newest_event(self.journal)
        if not newest:return
        key=(newest['time'],newest['title'],newest['message'])
        if self.last_key==key:return
        self.last_key=key
        if load_state(self.state_path)['dnd']:return
        self.title.setText(newest['app']+' · '+newest['title'])
        self.message.setText(newest['message'])
        screen=self.screen()
        if screen is not None:
            rect=screen.availableGeometry()
            self.move(rect.right()-self.width()-20,rect.bottom()-self.sizeHint().height()-90)
        self.show()
        self.dismiss_timer.start(5500)

    def closeEvent(self,event):
        self.poller.stop()
        self.dismiss_timer.stop()
        event.accept()
