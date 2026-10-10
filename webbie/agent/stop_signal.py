"""Stop-only local signal between Webbie speech and consented GUI desktop tasks.

This signal can ONLY revoke work. It cannot wake Webbie, approve a task,
launch apps, or send arbitrary GUI commands.
"""
from pathlib import Path
import os
import stat

def stop_path(runtime=None):
    folder = Path(runtime) if runtime else Path(
        os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'
    if folder.is_symlink():
        raise PermissionError('Unsafe Webbie runtime path')
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = folder.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise PermissionError('Webbie stop signal must belong to current user')
    return folder / 'webbie-stop-request'


def request_stop(runtime=None):
    path = stop_path(runtime)
    if path.is_symlink():
        raise PermissionError('Unsafe Webbie stop signal')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_TRUNC, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise PermissionError('Invalid Webbie stop signal owner')
        os.write(fd, b'STOP\n')
    finally:
        os.close(fd)


def consume_stop(runtime=None):
    path = stop_path(runtime)
    try:
        if path.is_symlink():
            return False
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            return False
        data = path.read_bytes()[:8]
        path.unlink()
        return data == b'STOP\n'
    except FileNotFoundError:
        return False
    except OSError:
        return False
