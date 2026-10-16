#!/usr/bin/env python3
"""Opt-in per-user Spider Audio Studio private beta installer.

No sudo, root modifications, services, music deletion, or existing app
replacement. Creates a versioned application directory and desktop entry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

VERSION_RE=re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-(?:beta|dev|rc)[0-9]*$")
DESKTOP_ID="com.spideros.AudioStudio.Beta-"

def _safe_relative(name):
    if not isinstance(name,str) or not name or name.startswith("/"):
        return False
    return (not Path(name).is_absolute() and
            all(x not in ("",".","..") for x in name.split("/"))
            and not any(ord(x)<32 or ord(x)==127 for x in name))

def _safe_under(home,path):
    if not path.is_relative_to(home):
        raise ValueError("The beta installer writes only inside the user's home.")
    current=home
    if current.is_symlink():
        raise ValueError("Home is a symlink.")
    for piece in path.relative_to(home).parts:
        current=current/piece
        if current.is_symlink():
            raise ValueError("Symlink in install destination.")
    return path

def verify(bundle):
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("Not an extracted regular Studio application package.")
    entry=bundle/"run_spider_audio_studio.py"
    data_file=bundle/"manifest.json"
    if (entry.is_symlink() or data_file.is_symlink() or
            not entry.is_file() or not data_file.is_file()
            or data_file.stat().st_size>1_000_000):
        raise ValueError("Missing or redirected application verification files.")
    data=json.loads(data_file.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.get("schema")!=1:
        raise ValueError("Unsupported Studio package manifest.")
    version=data.get("version")
    if not isinstance(version,str) or not VERSION_RE.fullmatch(version):
        raise ValueError("Unexpected Studio release version.")
    if data.get("private_developer_preview") is not True:
        raise ValueError("Only explicit private beta packages are accepted.")
    files=data.get("files")
    if not isinstance(files,dict) or not 40<=len(files)<=900:
        raise ValueError("Incomplete native Studio source manifest.")
    total=0
    for name,digest in files.items():
        if (not _safe_relative(name) or type(digest) is not str or
                re.fullmatch(r"[0-9a-f]{64}",digest) is None):
            raise ValueError("Invalid Studio manifest filename or checksum.")
        path=bundle/"app"/name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or linked bundled application source.")
        size=path.stat().st_size
        if size>10*1024*1024:
            raise ValueError("Unexpectedly large bundled source.")
        total+=size
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError("Bundled application source checksum mismatch.")
    if total>80*1024*1024:
        raise ValueError("Native Studio payload exceeded safe size limits.")
    subprocess.run([sys.executable,str(entry),"--verify-only"],
                   stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE,text=True,timeout=45,check=True)
    return data

def _quote_exec(value):
    raw=str(value)
    if any(ch in raw for ch in ('"',"\\",chr(96),"$","\n","\r","\x00")):
        raise ValueError("Unsafe local desktop launch path characters.")
    return '"'+raw+'"'

def install(bundle,home=None):
    bundle=Path(bundle).expanduser().absolute()
    home=Path(home or Path.home()).expanduser().absolute()
    data=verify(bundle)
    version=data["version"]
    versions=_safe_under(
        home,home/".local"/"share"/"spider-audio-studio"/"versions")
    location=_safe_under(home,versions/version)
    apps=_safe_under(home,home/".local"/"share"/"applications")
    desktop=_safe_under(home,apps/(DESKTOP_ID+version.replace(".","_")+".desktop"))
    if location.exists() or location.is_symlink():
        raise FileExistsError("This Studio beta is installed already; no replacements made.")
    if desktop.exists() or desktop.is_symlink():
        raise FileExistsError("The exact versioned desktop entry already exists.")
    versions.mkdir(mode=0o700,parents=True,exist_ok=True)
    apps.mkdir(mode=0o755,parents=True,exist_ok=True)
    _safe_under(home,location)
    _safe_under(home,desktop)
    # Exclusive mkdir means another install cannot replace a real owner app.
    location.mkdir(mode=0o700,exist_ok=False)
    (location/"app").mkdir(mode=0o700)
    for name in sorted(data["files"]):
        target=location/"app"/name
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (bundle/"app"/name).open("rb") as inp,target.open("xb") as out:
            shutil.copyfileobj(inp,out,1024*1024)
        target.chmod(0o600)
    for name in ("manifest.json","run_spider_audio_studio.py"):
        target=location/name
        with (bundle/name).open("rb") as inp,target.open("xb") as out:
            shutil.copyfileobj(inp,out)
        target.chmod(0o700 if name.endswith(".py") else 0o600)
    subprocess.run(
        [sys.executable,str(location/"run_spider_audio_studio.py"),"--verify-only"],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,text=True,timeout=45,check=True)
    entry=location/"run_spider_audio_studio.py"
    icon=location/"app"/"branding"/"spider-apps"/"icons"/"spider-audio-studio.svg"
    lines=[
        "[Desktop Entry]","Type=Application",
        "Name=Spider Audio Studio (Beta "+version+")",
        "Comment=Record, arrange and mix music in the native Spider Studio",
        "Exec="+_quote_exec(Path(sys.executable))+" "+_quote_exec(entry),
        "Icon="+str(icon),"Terminal=false","StartupNotify=true",
        "Categories=AudioVideo;Audio;Recorder;",
        "Keywords=music;audio;recording;guitar;mixing;",
        "X-SpiderStudio-PrivateBeta=true",""]
    with desktop.open("x",encoding="utf-8") as writer:
        writer.write("\n".join(lines))
    desktop.chmod(0o644)
    return location,desktop

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check",action="store_true")
    modes.add_argument("--install",action="store_true")
    args=parser.parse_args(argv)
    if hasattr(os,"geteuid") and os.geteuid()==0:
        parser.exit(2,"Do not run this per-user installer as root.\n")
    bundle=Path(__file__).resolve().parent
    try:
        if args.check:
            data=verify(bundle)
            print("SPIDER AUDIO STUDIO PACKAGE VERIFIED:",data["version"])
        else:
            app,desktop=install(bundle)
            print("Installed privately:",app)
            print("Application-menu shortcut:",desktop)
            print("No Spider OS files, Webbie/Nova or existing music were touched.")
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        parser.exit(2,"Spider Audio Studio user installation blocked: "+str(error)+"\n")

if __name__=="__main__":
    main()
