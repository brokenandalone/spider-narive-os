"""Individual workspace labs inside the existing Universal Control Center."""
from __future__ import annotations
from pathlib import Path
import json
from .max_catalog import WORKSPACES,run
from .max_board import WorkspaceBoard


def attach_max(main,home,initial_workspace=None):
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (QWidget,QTabWidget,QVBoxLayout,QHBoxLayout,QFormLayout,
          QPushButton,QLineEdit,QTextEdit,QLabel,QFileDialog,QComboBox,QListWidget,
          QListWidgetItem,QInputDialog,QMessageBox)
    home=Path(home)
    parent=QWidget();outer=QVBoxLayout(parent)
    intro=QLabel('WORKSPACE MAX v4 · 15 independent labs · 137 owner-scoped operations · private boards. '
                 'Choose files manually. Nothing modifies resident Spider OS, radio, or Webbie.')
    intro.setWordWrap(True);outer.addWidget(intro)
    tabs=QTabWidget();tabs.setUsesScrollButtons(True);outer.addWidget(tabs,1)
    def create_lab(workspace,module):
        tab=QWidget();box=QVBoxLayout(tab)
        heading=QLabel(f'{workspace.upper()} · INDIVIDUAL WORKSPACE LAB')
        heading.setStyleSheet('font-weight:bold;color:#d3b7ff;font-size:15px')
        box.addWidget(heading)
        box.addWidget(QLabel('Read-only inspection plus manually saved private notes and tasks. No shell commands are executed.'))
        row=QHBoxLayout();box.addLayout(row)
        choices=QComboBox()
        for name in module.ACTIONS:choices.addItem(name.replace('-',' ').title(),name)
        choices.setMinimumWidth(200);row.addWidget(choices,2)
        folder=QLineEdit();folder.setReadOnly(True)
        folder.setPlaceholderText('Choose a local project directory for this workspace');row.addWidget(folder,4)
        def pick_path(dest=folder):
            p=QFileDialog.getExistingDirectory(main,'Select owner project folder',str(Path.home()))
            if p:dest.setText(p)
        button=QPushButton('Choose folder');button.clicked.connect(lambda checked=False:pick_path());row.addWidget(button,1)
        row=QHBoxLayout();box.addLayout(row)
        query=QLineEdit();query.setPlaceholderText('Optional search phrase, comma-separated names or filter')
        row.addWidget(query,1)
        results=QTextEdit();results.setReadOnly(True);results.setPlaceholderText('Inspection results will appear here.')
        def execute_workspace(w=workspace,ch=choices,path=folder,q=query,target=results):
            if not path.text().strip():return main.error(ValueError('Choose a project folder'))
            # Capture all GUI values on the Qt thread before dispatching worker.
            operation=ch.currentData();chosen_folder=path.text();search_phrase=q.text()
            def fn(cancel,progress):
                progress(f'Reviewing {w} selected project folder…')
                result=run(w,operation,chosen_folder,search_phrase)
                return {'cancelled':True} if cancel.is_set() else result
            def done(response):
                if not response.get('ok'):
                    target.setPlainText('BLOCKED: '+str(response.get('error')))
                else:
                    target.setPlainText(json.dumps(response['result'],indent=2,ensure_ascii=False,default=str)[:180_000])
            main.launch_worker(fn,on_done=done)
        b=QPushButton('Inspect selected operation');b.clicked.connect(lambda checked=False:execute_workspace());row.addWidget(b)
        box.addWidget(results,2)
        box.addWidget(QLabel('PRIVATE WORKSPACE BOARD · You decide what to save. Notes never execute as commands.'))
        board_list=QListWidget();box.addWidget(board_list,1)
        board_file=home/'workspace_max_boards.sqlite3'
        def refresh(w=workspace,target=board_list):
            with WorkspaceBoard(board_file) as board:records=board.list(w)
            target.clear()
            for record in records:
                label=f"{'✓' if record['status']=='done' else '○'} [{record['kind']}] {record['title']}"
                entry=QListWidgetItem(label);entry.setData(Qt.UserRole,record['id']);
                entry.setToolTip(record['detail'][:200]);target.addItem(entry)
        def add(kind,w=workspace,target=board_list):
            title,ok=QInputDialog.getText(main,f'{w} new {kind}','Title')
            if not ok or not title.strip():return
            detail,ok=QInputDialog.getMultiLineText(main,'Optional detail','Private notes (not a command)')
            if not ok:return
            try:
                with WorkspaceBoard(board_file) as board:board.add(w,title,detail,kind)
                refresh(w,target)
            except (ValueError,OSError,PermissionError) as exc:main.error(exc)
        def mark_done(w=workspace,target=board_list):
            if target.currentItem() is None:return main.error(ValueError('Select a board item'))
            try:
                with WorkspaceBoard(board_file) as board:board.set_status(target.currentItem().data(Qt.UserRole),'done')
                refresh(w,target)
            except (ValueError,OSError,KeyError) as exc:main.error(exc)
        row=QHBoxLayout();box.addLayout(row)
        for title,fn in [('Add task',lambda checked=False,w=workspace:add('task',w)),
                         ('Add note',lambda checked=False,w=workspace:add('note',w)),
                         ('Add review',lambda checked=False,w=workspace:add('review',w)),
                         ('Mark done',lambda checked=False:mark_done()),('Refresh',lambda checked=False:refresh())]:
            b=QPushButton(title);b.clicked.connect(fn);row.addWidget(b)
        try:refresh()
        except (OSError,ValueError,PermissionError) as exc:main.footer.setText(f'{workspace} board unavailable: {exc}')
        tabs.addTab(tab,workspace)
    for workspace,module in WORKSPACES.items():
        create_lab(workspace,module)
    main.tabs.addTab(parent,'Workspace MAX')
    if initial_workspace in WORKSPACES:
        tabs.setCurrentIndex(list(WORKSPACES).index(initial_workspace))
        main.tabs.setCurrentWidget(parent)
