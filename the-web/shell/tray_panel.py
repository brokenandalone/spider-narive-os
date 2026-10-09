"""StatusNotifier applications panel for The Web's existing taskbar."""
from PyQt5.QtCore import QThread,pyqtSignal,Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QLabel,QListWidget,QListWidgetItem,QPushButton,QMenu
from status_tray import get_status_items,activate_item,split_item,get_item_details,secondary_activate_item

class TrayWorker(QThread):
    ready=pyqtSignal(object)
    error=pyqtSignal(str)
    def __init__(self,operation='list',item=None,parent=None):
        super().__init__(parent);self.operation=operation;self.item=item
    def run(self):
        try:
            if self.operation=='list':
                self.ready.emit([get_item_details(item) for item in get_status_items()])
            elif self.operation=='activate':
                activate_item(self.item);self.ready.emit(None)
            elif self.operation=='secondary':
                secondary_activate_item(self.item);self.ready.emit(None)
        except (OSError,ValueError,RuntimeError) as error:
            self.error.emit(str(error))

class TrayPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('The Web · Background Apps')
        self.items=[]
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Background applications (StatusNotifier)'))
        self.status=QLabel('Checking for background apps…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.list=QListWidget();layout.addWidget(self.list)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.show_app_menu)
        self.refresh_button=QPushButton('Refresh background apps')
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button)
        self.launch_button=QPushButton('Open selected app')
        self.launch_button.clicked.connect(self.open_selected)
        layout.addWidget(self.launch_button)
        self.worker=None
        self.refresh()
    def _run(self,operation,item=None):
        if self.worker and self.worker.isRunning():return
        self.worker=TrayWorker(operation,item,self)
        self.refresh_button.setEnabled(False)
        self.launch_button.setEnabled(False)
        self.worker.ready.connect(self._done)
        self.worker.error.connect(self.status.setText)
        self.worker.finished.connect(lambda: (self.refresh_button.setEnabled(True),
                                               self.launch_button.setEnabled(True)))
        self.worker.start()
    def refresh(self):
        self.status.setText('Checking the session notifier watcher…')
        self._run('list')
    def _done(self,result):
        if isinstance(result,list):
            self.items=result
            self.list.clear()
            for item in result:
                if not isinstance(item,dict):continue
                label=str(item.get('title',item.get('service','App')))[:90]
                label+=' · '+str(item.get('status','Unknown'))[:28]
                row=QListWidgetItem(label)
                # Resolve a themed icon name only. App-supplied file paths
                # or pixmaps must not be opened by the tray.
                icon_name=item.get('icon_name','')
                if (isinstance(icon_name,str) and icon_name and
                        '/' not in icon_name and len(icon_name)<=120):
                    icon=QIcon.fromTheme(icon_name)
                    if not icon.isNull():row.setIcon(icon)
                self.list.addItem(row)
            self.status.setText(f'{len(result)} background apps found.' if result else
                 'No registered StatusNotifier apps found. A watcher service may be unavailable.')
        else:
            self.status.setText('Activation request sent to the selected app.')
    def open_selected(self):
        index=self.list.currentRow()
        if index<0 or index>=len(self.items):return
        self._run('activate',self.items[index]['id'])
    def show_app_menu(self,point):
        index=self.list.indexAt(point).row()
        if index<0 or index>=len(self.items):return
        item=self.items[index]
        menu=QMenu(self)
        menu.addAction('Open application',lambda:self._run('activate',item['id']))
        menu.addAction('Secondary action',lambda:self._run('secondary',item['id']))
        if item.get('menu'):
            menu.addSeparator()
            note=menu.addAction('Application provides a native menu')
            note.setEnabled(False)
        menu.exec_(self.list.mapToGlobal(point))

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():event.ignore()
        else:event.accept()
