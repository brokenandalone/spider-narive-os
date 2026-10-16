#!/usr/bin/env python3
"""Explicit, transactional per-user Spider Audio Studio private beta installer.

Never use sudo or modify Spider OS. Every version has a separate directory
and desktop shortcut. A copy or verification failure must not leave behind a
partially installed version that the owner cannot safely retry.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

VERSION_RE=re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-(?:beta|dev|rc)[0-9]*$")
DESKTOP_ID="com.spideros.AudioStudio.Beta-"
COPIED=("manifest.json","run_spider_audio_studio.py")

def _safe_relative(name):
    if type(name) is not str or not name or name.startswith(("/","\\")):
        return False
    return (not Path(name).is_absolute()
            and "\\" not in name
            and all(part not in ("",".","..") for part in name.split("/"))
            and not any(ord(ch)<32 or ord(ch)==127 for ch in name))

def _safe_under(home,path):
    """Reject a pre-existing symlink in any intended install directory."""
    if not path.is_relative_to(home):
        raise ValueError("Only a private path inside the owner's home is permitted.")
    current=home
    if current.is_symlink():
        raise ValueError("The home location must not be a symlink.")
    for item in path.relative_to(home).parts:
        current=current/item
        if current.is_symlink():
            raise ValueError("Symlink in an installation destination.")
    return path

def verify(bundle):
    """Inspect source hashes before installing, with no audio device activity."""
    bundle=Path(bundle).expanduser().absolute()
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("Select a regular extracted Spider Studio beta.")
    app=bundle/"app"
    if app.is_symlink() or not app.is_dir():
        raise ValueError("The packaged application source directory is unsafe.")
    entry=bundle/"run_spider_audio_studio.py"
    data_file=bundle/"manifest.json"
    if (entry.is_symlink() or data_file.is_symlink()
            or not entry.is_file() or not data_file.is_file()
            or data_file.stat().st_size>1_000_000):
        raise ValueError("Studio's manifest or launcher is missing or redirected.")
    data=json.loads(data_file.read_text(encoding="utf-8"))
    if type(data) is not dict or data.get("schema")!=1:
        raise ValueError("Unexpected application manifest schema.")
    version=data.get("version")
    if type(version) is not str or not VERSION_RE.fullmatch(version):
        raise ValueError("Unexpected Spider Audio Studio version.")
    if data.get("private_developer_preview") is not True:
        raise ValueError("Only an explicitly labeled private beta can be installed.")
    files=data.get("files")
    if type(files) is not dict or not 40<=len(files)<=900:
        raise ValueError("The native Studio source inventory is incomplete.")
    total=0
    for name,digest in files.items():
        if (not _safe_relative(name) or type(digest) is not str
                or re.fullmatch(r"[0-9a-f]{64}",digest) is None):
            raise ValueError("A source name or checksum is not safe.")
        item=app/name
        if (item.is_symlink() or not item.is_file()
                or not item.resolve().is_relative_to(app.resolve())):
            raise ValueError("A packaged source file is missing or redirected.")
        size=item.stat().st_size
        if size>10*1024*1024:
            raise ValueError("Oversized source is not accepted.")
        total+=size
        if hashlib.sha256(item.read_bytes()).hexdigest()!=digest:
            raise ValueError("Packaged application source checksum mismatch.")
    if total>80*1024*1024:
        raise ValueError("Package is unexpectedly large.")
    extras=data.get("extras")
    if type(extras) is not dict or not 4<=len(extras)<=12:
        raise ValueError("Missing beta launcher disclosures or installer metadata.")
    for name,digest in extras.items():
        if (not _safe_relative(name) or "/" in name or
                type(digest) is not str or
                re.fullmatch(r"[0-9a-f]{64}",digest) is None):
            raise ValueError("Invalid beta installer or legal notice manifest.")
        item=bundle/name
        if item.is_symlink() or not item.is_file() or item.stat().st_size>1_000_000:
            raise ValueError("Missing or linked beta installer or legal notice.")
        if hashlib.sha256(item.read_bytes()).hexdigest()!=digest:
            raise ValueError("Beta installer or legal notice checksum mismatch.")
    completed=subprocess.run(
        [sys.executable,str(entry),"--verify-only"],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,text=True,timeout=45,check=False)
    if completed.returncode!=0:
        raise ValueError("Studio package verification command failed.")
    return data

def _quote_exec(value):
    value=str(value)
    if any(ch in value for ch in ('"',"\\",chr(96),"$","\n","\r","\x00")):
        raise ValueError("A desktop launch path has unsafe characters.")
    return '"'+value+'"'

def _copy_checked(source,target,expected_sha=None):
    if source.is_symlink() or not source.is_file():
        raise ValueError("Source changed during the installation.")
    digest=hashlib.sha256()
    with source.open("rb") as incoming,target.open("xb") as output:
        for data in iter(lambda:incoming.read(1024*1024),b""):
            digest.update(data)
            output.write(data)
    if expected_sha is not None and digest.hexdigest()!=expected_sha:
        raise ValueError("Source changed during copy. Installation cancelled.")
    target.chmod(0o700 if target.name=="run_spider_audio_studio.py" else 0o600)

def install(bundle,home=None):
    """Commit only a fully verified version; failed attempts leave no version.

    A per-user advisory lock serializes cooperating installer instances.
    Staging uses owner-only permissions. Neither location nor menu entry
    overwrites prior installs; source recordings are never examined.
    """
    bundle=Path(bundle).expanduser().absolute()
    home=Path(home or Path.home()).expanduser().absolute()
    if hasattr(os,"geteuid") and os.geteuid()==0 and home==Path.home().absolute():
        raise ValueError("Do not install the Studio beta under root's own account.")
    info=verify(bundle)
    version=info["version"]
    root=_safe_under(home,home/".local"/"share"/"spider-audio-studio"/"versions")
    location=_safe_under(home,root/version)
    menu=_safe_under(home,home/".local"/"share"/"applications")
    desktop=_safe_under(home,menu/(DESKTOP_ID+version.replace(".","_")+".desktop"))
    # Check the existing paths before modifying any directory.
    if location.exists() or location.is_symlink():
        raise FileExistsError("This version is already installed; nothing replaced.")
    if desktop.exists() or desktop.is_symlink():
        raise FileExistsError("This desktop entry already exists; nothing replaced.")
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    menu.mkdir(parents=True,exist_ok=True,mode=0o755)
    _safe_under(home,location)
    _safe_under(home,desktop)
    lock_path=_safe_under(home,root/".install.lock")
    if lock_path.is_symlink():
        raise ValueError("Unsafe installer lock location.")
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if location.exists() or desktop.exists() or desktop.is_symlink():
            raise FileExistsError("Another installer already published this version.")
        stage=Path(tempfile.mkdtemp(prefix=".installing-",dir=root))
        desktop_created=False
        published=False
        try:
            (stage/"app").mkdir(mode=0o700)
            for name,digest in sorted(info["files"].items()):
                target=stage/"app"/name
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                _copy_checked(bundle/"app"/name,target,digest)
            for name in COPIED:
                _copy_checked(bundle/name,stage/name)
            for name,digest in sorted(info["extras"].items()):
                _copy_checked(bundle/name,stage/name,digest)
            # Verify the completed staged installation before publishing.
            result=subprocess.run(
                [sys.executable,str(stage/"run_spider_audio_studio.py"),
                 "--verify-only"],
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,text=True,timeout=45,check=False)
            if result.returncode:
                raise ValueError("Staged Studio source failed integrity check.")
            entry=location/"run_spider_audio_studio.py"
            icon=location/"app"/"branding"/"spider-apps"/"icons"/"spider-audio-studio.svg"
            document="\n".join((
                "[Desktop Entry]","Type=Application",
                "Name=Spider Audio Studio (Beta "+version+")",
                "Comment=Native recording, arranging and protected WAV mixing",
                "Exec="+_quote_exec(Path(sys.executable))+" "+_quote_exec(entry),
                "Icon="+str(icon),"Terminal=false","StartupNotify=true",
                "Categories=AudioVideo;Audio;Recorder;",
                "Keywords=music;guitar;vocals;audio;mixing;",
                "X-SpiderStudio-PrivateBeta=true",""))
            # Both file creation and final publish refuse existing owner data.
            # The menu entry is briefly unpublished until the verified folder
            # is renamed; cleanup below removes a failed entry.
            with desktop.open("x",encoding="utf-8") as writer:
                desktop_created=True
                writer.write(document)
            desktop.chmod(0o644)
            if location.exists() or location.is_symlink():
                raise FileExistsError("Destination became occupied during install.")
            stage.rename(location)
            published=True
        except BaseException:
            if not published:
                if desktop_created:
                    desktop.unlink(missing_ok=True)
                if stage.is_dir():
                    shutil.rmtree(stage)
            raise
        return location,desktop

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--install",action="store_true")
    options=parser.parse_args(argv)
    if hasattr(os,"geteuid") and os.geteuid()==0:
        parser.exit(2,"The Studio beta user installer must not be run as root.\n")
    bundle=Path(__file__).resolve().parent
    try:
        if options.check:
            info=verify(bundle)
            print("SPIDER AUDIO STUDIO VERIFIED:",info["version"])
        else:
            location,desktop=install(bundle)
            print("New application installation:",location)
            print("New app-menu shortcut:",desktop)
            print("Original recordings and Spider OS were untouched.")
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        parser.exit(2,"Spider Audio Studio installation blocked: "+str(error)+"\n")

if __name__=="__main__":
    main()
