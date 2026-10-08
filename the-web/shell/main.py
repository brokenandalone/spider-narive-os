#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QVBoxLayout, QWidget

SPIDER_ROOT = Path('/usr/local/lib/spider-os')
if not SPIDER_ROOT.exists():
    SPIDER_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SPIDER_ROOT / 'system'))
from apps import AppUnavailable, AUTHOR_HOME, author_command, media_command, studio_command
WORKSPACE_IMAGES = {'author': 'system'}

WALLPAPER = SPIDER_ROOT / 'branding' / 'wallpapers' / 'spider-os-wallpaper.png'

class WallpaperWidget(QWidget):
    """Paint the background on the actual central widget, not behind it."""

    def __init__(self):
        super().__init__()
        self._background = QPixmap()

    def set_background(self, pixmap):
        self._background = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._background.isNull() and self.width() and self.height():
            image = self._background.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (image.width() - self.width()) // 2
            y = (image.height() - self.height()) // 2
            painter.drawPixmap(0, 0, image, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor(8, 6, 11))
        painter.fillRect(self.rect(), QColor(8, 6, 11, 120))
        painter.end()


class TheWeb(QMainWindow):
    def __init__(self):
        super().__init__()
        self.wallpaper = None
        self.setWindowTitle('The Web | Spider OS')
        self.resize(1280, 820)
        self.setMinimumSize(1000, 650)
        self.build_ui()
        self.load_wallpaper()
        self.set_workspace('default')
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(5000)
        self.refresh_status()

    def build_ui(self):
        self.setStyleSheet('''
            QWidget#root { color:#f5eff8; }
            QLabel { color:#f5eff8; }
            QPushButton { background:rgba(70,25,105,225); border:1px solid #7e22ce; border-radius:9px; padding:11px; color:white; font-weight:bold; text-align:left; }
            QPushButton:hover { background:#6b21a8; border-color:#c084fc; }
            QFrame#card { background:rgba(18,13,24,225); border:1px solid #3c2946; border-radius:12px; }
        ''')
        root = WallpaperWidget(); root.setObjectName('root'); self.background_surface = root; self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(28,24,28,24)
        title = QLabel('SPIDER OS'); title.setFont(QFont('Sans Serif', 34, QFont.Bold)); title.setStyleSheet('color:#c084fc;')
        outer.addWidget(title)
        tagline = QLabel('YOUR LIFE. ONE WEB.'); tagline.setStyleSheet('color:#a99caf; font-size:14px; font-weight:bold;'); outer.addWidget(tagline)
        self.background_picker = QComboBox()
        for label, name in [('The Web', 'default'), ('Forage / Deep Forage', 'forage'),
                            ('Studio', 'studio'), ('Author', 'author'), ('Art Lab', 'art-lab'), ('Dev Bay', 'dev-bay'),
                            ('Study', 'study'), ('Media', 'media'), ('Kali Bay', 'kali-bay'),
                            ('System', 'system'), ('Recovery', 'recovery')]:
            self.background_picker.addItem(label, name)
        self.background_picker.currentIndexChanged.connect(
            lambda index: self.set_workspace(self.background_picker.itemData(index)))
        outer.addWidget(self.background_picker)
        body = QHBoxLayout(); outer.addLayout(body, 1)
        side = QVBoxLayout(); body.addLayout(side)
        for label, fn in [
            ('WEBBIE', self.open_webbie), ('FORAGE', self.open_forage), ('DEEP FORAGE', self.open_deep_forage),
            ('KALI BAY', self.open_kali), ('MEDIA CENTER', self.open_media), ('STUDY', self.open_study),
            ('STUDIO', self.open_studio), ('AUTHOR', self.open_author),
            ('TERMINAL', self.open_terminal), ('SYSTEM SETTINGS', self.open_settings),
        ]:
            b=QPushButton(label); b.setMinimumWidth(190); b.clicked.connect(fn); side.addWidget(b)
        side.addStretch(1)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); body.addWidget(scroll, 1)
        content = QWidget(); scroll.setWidget(content); center = QVBoxLayout(content)
        heading = QLabel('THE WEB'); heading.setFont(QFont('Sans Serif', 26, QFont.Bold)); heading.setStyleSheet('color:#e9d5ff;'); center.addWidget(heading)
        intro = QLabel('Native Spider OS home · Webbie · research · security · media · study'); intro.setStyleSheet('color:#b2a5ba;'); center.addWidget(intro)
        grid = QGridLayout(); center.addLayout(grid, 1)
        cards = [
            ('Webbie','Resident voice AI','Talk, launch, organize, assist',self.open_webbie),
            ('Forage','Search & discovery','Local knowledge + web search',self.open_forage),
            ('Deep Forage','Research','Multi-source research and synthesis',self.open_deep_forage),
            ('Kali Bay','Security workspace','Isolated full Kali environment',self.open_kali),
            ('Media Center','Spider Media Center','Music, video and recovered media package',self.open_media),
            ('Study','Education workspace','Courses, assignments, notes, research',self.open_study),
            ('Studio','Native creative workspace','Music, artwork and production tools',self.open_studio),
            ('Author','Independent writing workspace','Local manuscript editing and persistent session',self.open_author),
        ]
        for i,(name,sub,desc,fn) in enumerate(cards):
            frame=QFrame(); frame.setObjectName('card'); lay=QVBoxLayout(frame)
            n=QLabel(name); n.setStyleSheet('font-size:20px;font-weight:bold;color:#d8b4fe;'); lay.addWidget(n)
            s=QLabel(sub); s.setStyleSheet('font-weight:bold;color:#bca9c8;'); lay.addWidget(s)
            d=QLabel(desc); d.setWordWrap(True); d.setStyleSheet('color:#96899f;'); lay.addWidget(d); lay.addStretch(1)
            o=QPushButton('OPEN'); o.clicked.connect(fn); lay.addWidget(o)
            grid.addWidget(frame, i//2, i%2)
        self.service_status = QLabel(); self.service_status.setStyleSheet('color:#978b9f; padding-top:8px;'); center.addWidget(self.service_status)
        self.status = QLabel('Spider OS ready.'); self.status.setStyleSheet('color:#c7b9d1; padding-top:5px;'); outer.addWidget(self.status)

    def load_wallpaper(self):
        if WALLPAPER.exists(): self.wallpaper=QPixmap(str(WALLPAPER)); self.apply_wallpaper()
    def apply_wallpaper(self):
        if self.wallpaper is not None and not self.wallpaper.isNull():
            self.background_surface.set_background(self.wallpaper)

    def set_workspace(self,name):
        image = WALLPAPER if name == 'default' else SPIDER_ROOT / 'branding' / 'workspaces' / f'{WORKSPACE_IMAGES.get(name, name)}.png'
        if image.exists():
            self.wallpaper = QPixmap(str(image))
            self.apply_wallpaper()
        if hasattr(self, 'background_picker'):
            index = self.background_picker.findData(name)
            if index >= 0:
                self.background_picker.blockSignals(True)
                self.background_picker.setCurrentIndex(index)
                self.background_picker.blockSignals(False)
        runtime=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'spider-os'
        try: runtime.mkdir(parents=True,exist_ok=True); (runtime/'workspace').write_text(name,encoding='utf-8')
        except Exception: pass

    def launch(self,cmd,workspace='default',message='Opened.',cwd=None):
        self.set_workspace(workspace)
        try: subprocess.Popen([str(x) for x in cmd],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,cwd=cwd); self.status.setText(message)
        except Exception as e: self.status.setText(str(e))

    def open_webbie(self): self.launch(['python3',SPIDER_ROOT/'webbie/ui/webbie-ui.py'],'default','Webbie opened.')
    def open_forage(self): self.launch(['python3',SPIDER_ROOT/'forage/forage.py'],'forage','Forage opened.')
    def open_deep_forage(self): self.launch(['python3',SPIDER_ROOT/'forage/deep-forage/deep_forage.py'],'forage','Deep Forage opened.')
    def open_kali(self): self.launch([SPIDER_ROOT/'kali-bay/bin/kali-bay'],'kali-bay','Kali Bay opened.')
    def open_media(self):
        try:
            self.launch(media_command(),'media','Spider Media Center opened.')
        except AppUnavailable as error:
            self.status.setText(str(error))
    def open_studio(self):
        try:
            self.launch(studio_command(SPIDER_ROOT),'studio','Spider Studio opened.')
        except AppUnavailable as error:
            self.status.setText(str(error))
    def open_author(self):
        try:
            command = author_command()
            AUTHOR_HOME.mkdir(parents=True,exist_ok=True)
            for directory in ('Manuscripts','Lore','Snapshots'):
                (AUTHOR_HOME/directory).mkdir(exist_ok=True)
            self.launch(command,'author','Author editor opened.',cwd=AUTHOR_HOME)
        except (AppUnavailable, OSError) as error:
            self.status.setText(str(error))
    def open_study(self): self.launch(['python3',SPIDER_ROOT/'study/study.py'],'study','Study opened.')
    def open_terminal(self): self.launch(['konsole'],'default','Terminal opened.')
    def open_settings(self): self.launch(['systemsettings'],'system','System Settings opened.')

    def is_active(self,cmd):
        try: return subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2).returncode == 0
        except Exception: return False
    def refresh_status(self):
        webbie=self.is_active(['systemctl','--user','is-active','--quiet','webbie.service'])
        core=self.is_active(['systemctl','is-active','--quiet','spider-os.service'])
        ollama=self.is_active(['systemctl','is-active','--quiet','ollama.service'])
        dj=self.is_active(['systemctl','--user','is-active','--quiet','spider-ai-dj.service'])
        self.service_status.setText(f"Webbie: {'ONLINE' if webbie else 'OFFLINE'}   ·   Core: {'ONLINE' if core else 'OFFLINE'}   ·   Local AI: {'ONLINE' if ollama else 'OFFLINE'}   ·   AI DJ: {'ONLINE' if dj else 'OFFLINE'}")


def main():
    app=QApplication(sys.argv); app.setApplicationName('The Web'); w=TheWeb(); w.showMaximized(); sys.exit(app.exec_())
if __name__=='__main__': main()
