"""Opt-in local per-workspace tasks and reference notes. Nothing executes."""
from __future__ import annotations
import sqlite3,os,uuid
from datetime import datetime,timezone
from pathlib import Path
from .security import ensure_private_folder
from .max_catalog import WORKSPACES

def stamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')

class WorkspaceBoard:
    def __init__(self,path):
        self.path=Path(path).expanduser().absolute()
        ensure_private_folder(self.path.parent)
        if self.path.is_symlink():raise PermissionError('Workspace board symlink denied')
        self.db=sqlite3.connect(self.path,timeout=6)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=6000')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS workspace_notes(
            id TEXT PRIMARY KEY, workspace TEXT NOT NULL, kind TEXT NOT NULL,
            title TEXT NOT NULL, detail TEXT NOT NULL, status TEXT NOT NULL,
            created TEXT NOT NULL, updated TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS workspace_search_idx ON workspace_notes(workspace,status,created);
        ''')
        self.db.commit();os.chmod(self.path,0o600)
    def __enter__(self):return self
    def __exit__(self,*args):self.db.close()
    def add(self,workspace,title,detail='',kind='task'):
        if workspace not in WORKSPACES:raise ValueError('Unknown workspace')
        if kind not in ('task','note','review'):raise ValueError('Unrecognized note type')
        title=str(title).strip();detail=str(detail).strip()
        if not 1<=len(title)<=180 or len(detail)>4000:raise ValueError('Title length 1..180, detail max 4000')
        id=str(uuid.uuid4());ts=stamp()
        with self.db:self.db.execute('INSERT INTO workspace_notes VALUES (?,?,?,?,?,?,?,?)',
                                     (id,workspace,kind,title,detail,'open',ts,ts))
        return id
    def list(self,workspace,status=None,limit=120):
        if workspace not in WORKSPACES:raise ValueError('Unknown workspace')
        if status is not None and status not in ('open','done'):raise ValueError('Invalid status')
        if not 1<=limit<=500:raise ValueError('Bad limit')
        sql='SELECT * FROM workspace_notes WHERE workspace=?';params=[workspace]
        if status:sql+=' AND status=?';params.append(status)
        sql+=' ORDER BY updated DESC LIMIT ?';params.append(limit)
        return [dict(row) for row in self.db.execute(sql,params)]
    def set_status(self,id,status):
        if status not in ('open','done'):raise ValueError('Invalid status')
        with self.db:
            cur=self.db.execute('UPDATE workspace_notes SET status=?,updated=? WHERE id=?',(status,stamp(),str(id)))
            if cur.rowcount!=1:raise KeyError('Workspace task not found')
    def search(self,workspace,phrase):
        phrase=str(phrase).strip()
        if not phrase or len(phrase)>160:raise ValueError('Search phrase required')
        return [r for r in self.list(workspace,limit=500) if phrase.casefold() in (r['title']+' '+r['detail']).casefold()][:100]
