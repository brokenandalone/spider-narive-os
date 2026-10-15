"""Conservative local file, store, and URL boundaries.

No elevation, background jobs, shell-command execution, or secret collection.
"""
from __future__ import annotations
import hashlib
import ipaddress
import os
from pathlib import Path
import socket
import stat
import tempfile
import json
from urllib.parse import urlsplit

MAX_TEXT_BYTES=256_000
BANNED_PARTS={'.git','.ssh','.gnupg','.aws','.config','.local','.mozilla','.cache',
              '__pycache__','node_modules','venv','.venv','secrets','credentials'}
BANNED_SUFFIXES={'.key','.pem','.p12','.pfx','.sqlite','.db','.env','.kdbx'}

def _sensitive(path: Path)->bool:
    return any(p.lower() in BANNED_PARTS or p.lower().startswith('.env') for p in path.parts) or path.suffix.lower() in BANNED_SUFFIXES

def ensure_private_folder(folder: Path):
    """Create only a user-selected local directory; refuse symlinked ancestors."""
    folder=Path(folder).expanduser().absolute()
    current=Path(folder.anchor)
    for item in folder.parts[1:]:
        current=current/item
        if current.is_symlink():
            raise ValueError('Symlinked data directory not allowed: '+str(current))
        if current.exists():
            if not current.is_dir():
                raise ValueError('Data path is not a directory')
        else:
            current.mkdir(mode=0o700)
    # Do not chmod pre-existing ancestor directories. Only our data root.
    folder.chmod(0o700)
    return folder

def atomic_json(path, data):
    path=Path(path)
    ensure_private_folder(path.parent)
    if path.is_symlink():
        raise ValueError('Refusing symlinked output')
    payload=json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
    if len(payload.encode())>2_000_000:
        raise ValueError('Report too large')
    fd,tmp=tempfile.mkstemp(prefix='.spider-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            os.fchmod(stream.fileno(),0o600)
            stream.write(payload)
            stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def selected_file(path, root, max_bytes=MAX_TEXT_BYTES, allow_binary=False):
    """Read only non-secret regular files within a user-specified root."""
    root=Path(root).expanduser().absolute()
    path=Path(path).expanduser().absolute()
    if not path.is_relative_to(root):
        raise ValueError('Outside selected scope')
    rel=path.relative_to(root)
    if _sensitive(rel):
        raise ValueError('Sensitive path is excluded')
    if root.is_symlink() or path.is_symlink():
        raise ValueError('Symlink not allowed')
    for parent in path.parents:
        if parent==root: break
        if parent.is_symlink(): raise ValueError('Symlinked ancestor excluded')
    st=path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size>max_bytes:
        raise ValueError('Not a regular file within size limit')
    with path.open('rb') as f: raw=f.read(max_bytes+1)
    if len(raw)>max_bytes: raise ValueError('Size changed during read')
    if not allow_binary and b'\x00' in raw: raise ValueError('Binary source excluded')
    return raw

def hash_selected(path, root, max_bytes=64*1024*1024):
    """Bounded, symlink-free digest from a user-selected regular file."""
    root=Path(root).expanduser().absolute();path=Path(path).expanduser().absolute()
    if not path.is_relative_to(root): raise ValueError('Outside scope')
    if path.is_symlink() or root.is_symlink(): raise ValueError('Symlink')
    st=path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size>max_bytes: raise ValueError('File unavailable or oversized')
    h=hashlib.sha256()
    with path.open('rb') as f:
        total=0
        while chunk:=f.read(1024*1024):
            total+=len(chunk)
            if total>max_bytes: raise ValueError('File changed or oversized')
            h.update(chunk)
    if total!=st.st_size: raise ValueError('File size changed during scan')
    return h.hexdigest()

def validate_public_https(url, resolver=socket.getaddrinfo):
    """Return (host, resolved public IP, path), requiring only HTTPS port 443.

    Every result of DNS resolution must be public; pin the resulting IP in the
    HTTP connection to prevent check/use DNS rebinding.
    """
    if not isinstance(url,str) or len(url)>2048 or any(ord(c)<33 for c in url):
        raise ValueError('Invalid HTTPS URL')
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError('Public HTTPS only, no credentials or fragments')
    try: port=p.port or 443
    except ValueError: raise ValueError('Invalid port')
    if port!=443: raise ValueError('Only standard HTTPS allowed')
    host=p.hostname.rstrip('.').lower()
    try:
        parsed_ip=ipaddress.ip_address(host)
    except ValueError:
        parsed_ip=None
    if parsed_ip is not None:
        raise ValueError('Literal IP address is not permitted')
    if '.' not in host or host.endswith(('.local','.internal','.test','.example','.invalid','.localhost')):
        raise ValueError('Non-public hostname')
    if any(not x or len(x)>63 or x.startswith('-') or x.endswith('-') or not all(c.isascii() and (c.isalnum() or c=='-') for c in x) for x in host.split('.')):
        raise ValueError('Invalid host')
    ips=[]
    for address in resolver(host,443,proto=socket.IPPROTO_TCP):
        ip=ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError('DNS contains private or reserved address')
        ips.append(str(ip))
    if not ips: raise ValueError('No public address returned')
    path=(p.path or '/')+('?' + p.query if p.query else '')
    return host,ips[0],path
