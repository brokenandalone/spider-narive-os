"""StatusNotifier applications panel for The Web's existing taskbar."""
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QLabel,QListWidget,QPushButton
from status_tray import get_status_items,activate_item,split_item

class TrayWorker(QThread):
    ready=pyqtSignal(object)
    error=pyqtSignal(str)
    def __init__(self,operation='list',item=None,parent=None):
        super().__init__(parent);self.operation=operation;self.item=item
    def run(self):
        try:
            if self.operation=='list':self.ready.emit(get_status_items())
            elif self.operation=='activate':
                activate_item(self.item);self.ready.emit(None)
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
                try:service,_=split_item(item)
                except ValueError:continue
                self.list.addItem(service)
            self.status.setText(f'{len(result)} background apps found.' if result else
                 'No registered StatusNotifier apps found. A watcher service may be unavailable.')
        else:
            self.status.setText('Activation request sent to the selected app.')
    def open_selected(self):
        index=self.list.currentRow()
        if index<0 or index>=len(self.items):return
        self._run('activate',self.items[index])
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():event.ignore()
        else:event.accept()
