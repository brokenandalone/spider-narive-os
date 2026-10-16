"""Portable, verified, non-destructive Spider Audio Studio song archives.

Archives only verified session.json, original independent session WAVs and
private mix presets. They never include arbitrary source_path file targets,
generated model weights, AI voices, external sample banks, or other files.
Restore is staged and SHA-256 verified before publication as a NEW project.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
import zipfile
try:
    from .session_project import inspect_session
    from .multitrack import DEFAULT_OUTPUT,MAX_TOTAL_BYTES,SessionError
    from .session_presets import PRESET_FILE,MAX_PRESET_BYTES
except ImportError:
    from session_project import inspect_session
    from multitrack import DEFAULT_OUTPUT,MAX_TOTAL_BYTES,SessionError
    from session_presets import PRESET_FILE,MAX_PRESET_BYTES

LIMIT=MAX_TOTAL_BYTES+16*1024*1024
MAX_PRESETS=100
MAX_MEMBERS=MAX_PRESETS+26
ARCHIVE_NAME="spider-session-index.json"
HASH=re.compile(r"^[a-f0-9]{64}$")
WAV_NAME=re.compile(r"^\d{2}-[a-z_]+\.wav$")


def _verified_files(folder,session):
    sources={"session.json":folder/"session.json"}
    expected_hashes={}
    for track in session["tracks"]:
        name=track["filename"]
        if WAV_NAME.fullmatch(name) is None:
            raise SessionError("Unexpected verified WAV filename.")
        sources[name]=folder/name
        expected_hashes[name]=track["sha256"]
    presets=folder/"mix-presets"
    if presets.is_symlink():
        raise SessionError("The saved preset folder may not be redirected.")
    if presets.exists():
        if not presets.is_dir():
            raise SessionError("Invalid preset folder.")
        for entry in presets.iterdir():
            if (entry.is_symlink() or not entry.is_file() or
                    PRESET_FILE.fullmatch(entry.name) is None or
                    not 0<entry.stat().st_size<=MAX_PRESET_BYTES):
                raise SessionError("Unrecognized saved mix preset; archive was not created.")
            if len(sources)>=MAX_PRESETS+25:
                raise SessionError("Limit of 100 mix presets per backup.")
            sources["mix-presets/"+entry.name]=entry
    size=0
    for name,path in sources.items():
        if path.is_symlink() or not path.is_file():
            raise SessionError("A song component is missing or linked.")
        size+=path.stat().st_size
        if size>LIMIT:
            raise SessionError("A Spider song backup exceeds its size limit.")
    return sources,expected_hashes


def _checked_copy(reader,writer,limit,expected=None):
    amount=0
    digest=hashlib.sha256()
    while True:
        block=reader.read(1024*1024)
        if not block:
            break
        amount+=len(block)
        if amount>limit:
            raise SessionError("A backup member exceeded its validated size.")
        writer.write(block)
        digest.update(block)
    value=digest.hexdigest()
    if expected is not None and expected!=value:
        raise SessionError("A recording or backup member changed during copying.")
    return amount,value


def create_backup(folder,output_file):
    directory=Path(folder).expanduser()
    if directory.is_symlink() or not directory.is_dir():
        raise SessionError("Choose one local saved Studio session.")
    session=inspect_session(directory)
    sources,originals=_verified_files(directory,session)
    output=Path(output_file).expanduser()
    if output.suffix.lower()!=".zip" or output.is_symlink() or output.exists():
        raise SessionError("Choose a NEW .zip backup name.")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise SessionError("Choose an existing, real destination folder.")
    fd,temp=tempfile.mkstemp(prefix=".spider-song-backup-",suffix=".part",dir=output.parent)
    os.close(fd)
    os.chmod(temp,0o600)
    try:
        index={"schema":1,"application":"Spider Audio Studio",
               "project_title":session["title"],"members":{}}
        with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            for name,path in sorted(sources.items()):
                with path.open("rb") as original, archive.open(name,"w",force_zip64=True) as stored:
                    size,digest=_checked_copy(
                        original,stored,LIMIT,originals.get(name))
                index["members"][name]={"size":size,"sha256":digest}
            archive.writestr(ARCHIVE_NAME,json.dumps(index,sort_keys=True))
        if output.is_symlink() or output.exists():
            raise SessionError("A backup filename became occupied.")
        os.link(temp,output,follow_symlinks=False)
        os.chmod(output,0o600)
        return output
    finally:
        Path(temp).unlink(missing_ok=True)


def _index_archive(archive):
    names=archive.namelist()
    if (not 2<=len(names)<=MAX_MEMBERS or len(names)!=len(set(names)) or
            names.count(ARCHIVE_NAME)!=1):
        raise SessionError("Invalid or duplicate Spider song archive entries.")
    members=archive.infolist()
    for item in members:
        name=item.filename
        legal=(name=="session.json" or WAV_NAME.fullmatch(name) is not None or
               (name.startswith("mix-presets/") and
                PRESET_FILE.fullmatch(name[len("mix-presets/"):]) is not None)
               or name==ARCHIVE_NAME)
        if (not legal or item.is_dir() or item.compress_type!=zipfile.ZIP_STORED
                or item.flag_bits & 1 or item.file_size<1):
            raise SessionError("Archive has unsupported or unsafe file contents.")
    entry=archive.getinfo(ARCHIVE_NAME)
    if entry.file_size>128*1024:
        raise SessionError("Backup index is oversized.")
    try:
        index=json.loads(archive.read(ARCHIVE_NAME))
    except (OSError,ValueError,UnicodeError) as exc:
        raise SessionError("Invalid backup index.") from exc
    if (type(index) is not dict or index.get("schema")!=1
            or index.get("application")!="Spider Audio Studio"
            or type(index.get("members")) is not dict
            or set(index["members"])!=set(names)-{ARCHIVE_NAME}):
        raise SessionError("Backup index does not describe the complete project.")
    total=0
    for item in members:
        if item.filename==ARCHIVE_NAME:
            continue
        description=index["members"][item.filename]
        if (type(description) is not dict or
                set(description)!={"size","sha256"} or
                type(description["size"]) is not int or
                description["size"]!=item.file_size or
                type(description["sha256"]) is not str or
                HASH.fullmatch(description["sha256"]) is None):
            raise SessionError("Archive member size/hash metadata mismatch.")
        total+=item.file_size
        if total>LIMIT:
            raise SessionError("Backup expands beyond the supported session limit.")
    if "session.json" not in index["members"]:
        raise SessionError("Archived song has no session manifest.")
    return index,total


def restore_backup(archive_file,*,output_root=None):
    source=Path(archive_file).expanduser()
    if (source.is_symlink() or not source.is_file() or
            source.suffix.lower()!=".zip"):
        raise SessionError("Select a regular Spider Studio .zip backup.")
    root=Path(output_root if output_root is not None else DEFAULT_OUTPUT).expanduser()
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise SessionError("Choose a real destination for restored songs.")
    try:
        with zipfile.ZipFile(source,"r") as archive:
            index,total=_index_archive(archive)
            root.mkdir(parents=True,exist_ok=True,mode=0o700)
            if shutil.disk_usage(root).free<total+1024*1024:
                raise SessionError("Not enough free space to restore this song.")
            stage=Path(tempfile.mkdtemp(prefix=".restoring-",dir=root))
            os.chmod(stage,0o700)
            try:
                for name,info in sorted(index["members"].items()):
                    target=stage/name
                    target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
                    with archive.open(name,"r") as reader,target.open("xb") as writer:
                        copied,digest=_checked_copy(
                            reader,writer,info["size"],info["sha256"])
                    if copied!=info["size"]:
                        raise SessionError("A song backup was truncated.")
                    os.chmod(target,0o600)
                # Reinspect each recorded WAV, metadata and stored SHA
                # with the same project validator used by the live mixer.
                checked=inspect_session(stage)
                if checked["title"]!=index["project_title"]:
                    raise SessionError("The archived song title has changed.")
                destination=root/("session-restored-"+uuid.uuid4().hex)
                if destination.exists() or destination.is_symlink():
                    raise SessionError("The restored destination is occupied.")
                stage.rename(destination)
                return destination
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
    except (OSError,zipfile.BadZipFile,zipfile.LargeZipFile) as exc:
        raise SessionError("The Spider song backup could not be read or restored.") from exc
