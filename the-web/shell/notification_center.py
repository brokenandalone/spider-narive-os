"""Native notification history for The Web's existing taskbar.

Stores only notifications explicitly posted by The Web. A future separate
freedesktop DBus service is needed to display third-party app notifications.
"""
import json
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QCheckBox

MAX_ITEMS = 100

def load_state(path):
    try:
        path=Path(path)
        if path.is_symlink() or path.stat().st_size > 131072:
            return {'dnd':False,'items':[]}
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict): raise ValueError()
        items=data.get('items',[])
        if not isinstance(items,list): items=[]
        items=[x for x in items if isinstance(x,dict) and
               isinstance(x.get('title'),str) and isinstance(x.get('message'),str)]
        return {'dnd':data.get('dnd') is True,'items':items[-MAX_ITEMS:]}
    except (OSError,ValueError,TypeError):
        return {'dnd':False,'items':[]}

def save_state(path,state):
    path=Path(path)
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.is_symlink(): raise OSError('Notification settings must not be a symlink')
    import os,tempfile
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.notifications-')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(state,stream)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

class NotificationCenter(QWidget):
    def __init__(self,parent=None,path=None):
        super().__init__(parent)
        self.setWindowTitle('The Web Notifications')
        self.path=Path(path) if path is not None else Path.home()/'.local/state/spider-os/notifications.json'
        self.state=load_state(self.path)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Notifications from The Web'))
        self.dnd=QCheckBox('Do Not Disturb')
        self.dnd.setChecked(self.state['dnd'])
        self.dnd.toggled.connect(self.set_dnd)
        layout.addWidget(self.dnd)
        self.external_path=self.path.parent/'external-notifications.jsonl'
        self.history=QListWidget()
        self.history.setAccessibleName('The Web notification history')
        layout.addWidget(self.history)
        controls=QHBoxLayout()
        self.clear_button=QPushButton('Clear history')
        self.clear_button.clicked.connect(self.clear)
        controls.addWidget(self.clear_button)
        layout.addLayout(controls)
        layout.addWidget(QLabel('Other applications require a system notification bridge.'))
        self.refresh()

    def refresh(self):
        self.history.clear()
        try:
            if not self.external_path.is_symlink() and self.external_path.stat().st_size < 131072:
                lines=self.external_path.read_text(encoding='utf-8').splitlines()[-100:]
                for line in reversed(lines):
                    event=json.loads(line)
                    self.history.addItem(str(event.get('app','App'))[:40]+' · '+str(event.get('title',''))[:80]+'  '+str(event.get('message',''))[:300])
        except (OSError,ValueError,UnicodeError,TypeError):
            pass
        for item in reversed(self.state['items']):
            self.history.addItem(item['title'][:80]+'  '+item['message'][:300])

    def add_notification(self,title,message):
        item={'title':str(title)[:80],'message':str(message)[:300],
              'time':datetime.now().isoformat(timespec='seconds')}
        self.state['items']=(self.state['items']+[item])[-MAX_ITEMS:]
        save_state(self.path,self.state)
        self.refresh()
        return not self.state['dnd']

    def set_dnd(self,value):
        self.state['dnd']=bool(value)
        save_state(self.path,self.state)

    def clear(self):
        self.state['items']=[]
        save_state(self.path,self.state)
        self.refresh()
