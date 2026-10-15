"""Bounded, owner-selected analysis of local workspace projects.

No symlinks, dot-files, file execution, privilege changes or automatic writes.
Output is advisory; text from scanned files is untrusted data.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import re
import stat
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

EXCLUDED={'node_modules','.git','.svn','__pycache__','.venv','venv','private','secrets','credentials','backups','private-backups'}
MAX_FILES=1200
MAX_TEXT_BYTES=768_000
TEXT_EXT={'.txt','.md','.markdown','.py','.sh','.json','.yaml','.yml','.toml','.ini','.desktop','.html','.css','.js','.ts','.jsx','.tsx','.csv','.rst','.bib','.xml','.sql','.log','.docx','.service','.timer','.conf','.cfg'}
WORD=re.compile(r"\b[\w'-]+\b",re.U)

def selected(root):
    p=Path(root).expanduser().absolute()
    if not p.exists() or p.is_symlink() or not p.is_dir():
        raise ValueError('Choose a real, existing folder (not a symlink)')
    if p == Path('/'):
        raise ValueError('Select a project folder, not the whole filesystem')
    return p

def discover(root,extensions=None,limit=MAX_FILES):
    root=selected(root);result=[];excluded=0
    for current,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in EXCLUDED and not d.startswith('.') and
                not (Path(current)/d).is_symlink())
        for name in sorted(files):
            if name.startswith('.') or name.endswith(('~','.bak','.key','.pem','.p12','.pfx')):continue
            p=Path(current)/name
            if p.is_symlink():continue
            try:
                s=p.stat()
                if not stat.S_ISREG(s.st_mode):continue
            except OSError:continue
            if extensions is not None and p.suffix.lower() not in extensions:continue
            result.append(p)
            if len(result)>=limit:return result
    return result

def textfile(path):
    p=Path(path)
    if p.suffix.lower() not in TEXT_EXT or p.is_symlink():return ''
    try:
        if p.suffix.lower()=='.docx':
            if p.stat().st_size>6_000_000:return ''
            with zipfile.ZipFile(p) as z:
                meta=z.getinfo('word/document.xml')
                if meta.file_size>6_000_000:return ''
                raw=z.read(meta)
            xml=ET.fromstring(raw)
            paragraphs=[]
            for elem in xml.iter():
                if elem.tag.endswith('}p') or elem.tag=='p':
                    segment=''.join((node.text or '') for node in elem.iter()
                                    if node.tag.endswith('}t') or node.tag=='t')
                    if segment:paragraphs.append(segment)
            return '\n'.join(paragraphs)[:1_500_000]
        if p.stat().st_size>MAX_TEXT_BYTES:return ''
        return p.read_text('utf-8',errors='replace')
    except (OSError,UnicodeError,zipfile.BadZipFile,KeyError,ET.ParseError,RuntimeError,ValueError):return ''

def rel(root,p):return str(p.relative_to(selected(root)))

def summary(root,extensions=None):
    root=selected(root);files=discover(root,extensions)
    counts=Counter(p.suffix.lower() or '[none]' for p in files)
    return {'scope':str(root),'files_sampled':len(files),'sample_limit':MAX_FILES,
            'extension_counts':dict(counts.most_common(30)),'no_files_modified':True}

def digest_file(p,limit=80_000_000):
    p=Path(p)
    if p.is_symlink() or p.stat().st_size>limit:return None
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(512*1024),b''):h.update(chunk)
    return h.hexdigest()

def text_records(root,extensions=None):
    root=selected(root); extensions=extensions or TEXT_EXT
    for p in discover(root,extensions):
        t=textfile(p)
        if t:yield rel(root,p),t

def token_counts(text):
    return Counter(w.lower() for w in WORD.findall(text))

def quote_prefix(s,limit=160):
    return ' '.join(str(s).split())[:limit]

def standard_result(workspace,action,root,data):
    return {'workspace':workspace,'operation':action,'scope':str(selected(root)),
            'data':data,'read_only':True,
            'limitations':'Heuristic offline inspection. Review the original files before acting.'}

def counts(root,exts):
    files=discover(root,exts)
    return {'files':len(files),'extensions':dict(Counter(p.suffix.lower() for p in files))}
