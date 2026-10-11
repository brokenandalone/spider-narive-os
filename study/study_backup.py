"""Manual, private Study backup with consistent SQLite snapshot and checksums.

Archives contain the local Study database and course folder files, not Webbie
credentials, browser cookies or personal OneDrive configuration. Never overwrite
an archive and never silently perform restoration.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import zipfile

MAX_FILES = 2500
MAX_SINGLE_FILE = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MANIFEST_NAME = "manifest.json"
DB_MEMBER = "StudyData/study.db"


def _valid_member(name):
    parts = name.split("/")
    if (not parts or any(part in ("", ".", "..") for part in parts)
            or "\\" in name or "\x00" in name or name.startswith("/")
            or any(ord(char) < 32 for char in name)):
        raise ValueError("Unsafe archive member path.")
    return name


def _add_file(archive, file, member):
    checksum = hashlib.sha256()
    with file.open("rb") as source, archive.open(member, "w") as target:
        while True:
            data = source.read(131072)
            if not data:
                break
            checksum.update(data)
            target.write(data)
    return checksum.hexdigest()


def _study_files(root):
    files = []
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Study document folder must be a real directory.")
    # pathlib.rglob does not follow directory symlinks; also reject file links.
    for file in sorted(root.rglob("*")):
        if file.is_symlink() or not file.is_file():
            continue
        relative = file.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        name = _valid_member("CourseFiles/" + relative.as_posix())
        files.append((file, name))
        if len(files) > MAX_FILES - 1:
            raise ValueError("Too many Study files to create a bounded backup.")
    return files


def create_study_backup(db_path, documents_root, output):
    db_path, root, output = map(Path, (db_path, documents_root, output))
    if not db_path.is_file() or db_path.is_symlink():
        raise ValueError("Study database is unavailable or not a regular file.")
    if output.suffix.lower() != ".zip" or not output.parent.is_dir():
        raise ValueError("Choose a ZIP backup in an existing folder.")
    if output.is_symlink() or output.exists():
        raise FileExistsError("The chosen backup already exists; use a new filename.")
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Save the backup outside the Study course folder.")
    files = _study_files(root)
    total = sum(file.stat().st_size for file, _ in files)
    if any(file.stat().st_size > MAX_SINGLE_FILE for file, _ in files):
        raise ValueError("A Study file exceeds the 128 MB backup size limit.")
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Study documents exceed the 512 MB backup size limit.")
    fd_db, temp_db = tempfile.mkstemp(prefix=".study-db-", suffix=".sqlite",
                                      dir=output.parent)
    os.close(fd_db)
    fd_zip, temp_zip = tempfile.mkstemp(prefix=".study-zip-", suffix=".zip",
                                        dir=output.parent)
    os.close(fd_zip)
    try:
        with sqlite3.connect(
                "file:" + str(db_path.absolute()) + "?mode=ro", uri=True) as source:
            with sqlite3.connect(temp_db) as destination:
                source.backup(destination)
        snapshot = Path(temp_db)
        if snapshot.stat().st_size > MAX_SINGLE_FILE:
            raise ValueError("Study database snapshot exceeds 128 MB.")
        if total + snapshot.stat().st_size > MAX_TOTAL_BYTES:
            raise ValueError("Study backup exceeds 512 MB including database.")
        manifest = {
            "format": "spider-study-backup-v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "contents": {},
        }
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=5) as archive:
            for file, member in [(snapshot, DB_MEMBER)] + files:
                manifest["contents"][member] = {
                    "bytes": file.stat().st_size,
                    "sha256": _add_file(archive, file, member),
                }
            archive.writestr(MANIFEST_NAME,
                             json.dumps(manifest, indent=2, sort_keys=True))
        # Verify immediately before publishing, including all data hashes.
        verify_study_backup(temp_zip)
        os.link(temp_zip, output)  # Exclusive publish; never overwrite a race winner.
        os.chmod(output, 0o600)
        return {"files": len(files), "destination": str(output)}
    finally:
        Path(temp_db).unlink(missing_ok=True)
        Path(temp_zip).unlink(missing_ok=True)


def verify_study_backup(path):
    path = Path(path)
    if path.suffix.lower() != ".zip" or not path.is_file() or path.is_symlink():
        raise ValueError("Choose an existing regular ZIP backup.")
    if path.stat().st_size > MAX_TOTAL_BYTES:
        raise ValueError("Backup archive exceeds the verification size limit.")
    with zipfile.ZipFile(path, "r") as archive:
        members = archive.infolist()
        if len(members) > MAX_FILES + 2:
            raise ValueError("Backup contains too many files.")
        names = [item.filename for item in members]
        if len(set(names)) != len(names) or MANIFEST_NAME not in names:
            raise ValueError("Backup manifest is missing or contains duplicate names.")
        for info in members:
            _valid_member(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or info.is_dir():
                raise ValueError("Backup includes a link or directory member.")
            if info.file_size > MAX_SINGLE_FILE or info.flag_bits & 0x1:
                raise ValueError("Oversized or encrypted backup member.")
        if sum(info.file_size for info in members) > MAX_TOTAL_BYTES + 128_000:
            raise ValueError("Backup contents exceed the allowed size.")
        if archive.getinfo(MANIFEST_NAME).file_size > 128_000:
            raise ValueError("Backup manifest is too large.")
        manifest = json.loads(archive.read(MANIFEST_NAME))
        if manifest.get("format") != "spider-study-backup-v1":
            raise ValueError("Unrecognized Study backup format.")
        data = manifest.get("contents")
        if not isinstance(data, dict) or DB_MEMBER not in data:
            raise ValueError("Study database record is missing.")
        if set(data) != set(names) - {MANIFEST_NAME}:
            raise ValueError("Backup file list does not match the manifest.")
        for member, expected in data.items():
            info = archive.getinfo(_valid_member(member))
            if not isinstance(expected, dict) or expected.get("bytes") != info.file_size:
                raise ValueError("A backup member has the wrong size.")
            digest = hashlib.sha256()
            with archive.open(info, "r") as stream:
                for block in iter(lambda: stream.read(131072), b""):
                    digest.update(block)
            if digest.hexdigest() != expected.get("sha256"):
                raise ValueError("Backup checksum mismatch: " + member)
    return {"files": len(data)-1, "verified": True}
