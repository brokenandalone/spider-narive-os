#!/usr/bin/env python3
"""Build an isolated, owner-only Spider Audio Studio application archive.

This packages the EXISTING native SpiderStudio QWidget app and required Python
modules, not a clone, competing launcher UI, system update or deb installer.
No sudo, service changes, file replacement, music bundling or boot integration.
Commercial redistribution still needs separate license and dependency review.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

SOURCE=Path(__file__).resolve().parents[2]
VERSION="0.13.0-dev"
PACKAGE="Spider-Audio-Studio-"+VERSION
ROOTS=(
    "studio",
    "spider_max_source/spider_monster",
)
INDIVIDUAL=(
    "system/apps.py",
    "the-web/shell/workspace_max_native.py",
    "branding/spider-apps/icons/spider-audio-studio.svg",
)
ALLOW={".py",".json",".yaml",".yml",".txt",".md",".sh",".svg"}
MAX_ITEM=10*1024*1024
MAX_TOTAL=80*1024*1024

LAUNCHER='''#!/usr/bin/env python3
"""Run the original Spider Audio Studio from its isolated developer package."""
import hashlib
import json
import os
from pathlib import Path
import sys

home=Path(__file__).resolve().parent
app=home/"app"
manifest=home/"manifest.json"
try:
    data=json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema")!=1 or not isinstance(data.get("files"),dict):
        raise ValueError("Invalid Spider software manifest")
    if not 40<=len(data["files"])<=900:
        raise ValueError("Incomplete Studio runtime")
    for name,digest in data["files"].items():
        if (not isinstance(name,str) or name.startswith("/") or
                ".." in Path(name).parts or
                not isinstance(digest,str) or len(digest)!=64):
            raise ValueError("Unsafe Spider software manifest")
        source=app/name
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(app.resolve()):
            raise ValueError("Missing or linked app source: "+name)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
            raise ValueError("Studio package file changed: "+name)
except (OSError,ValueError,UnicodeError) as error:
    raise SystemExit("Spider Audio Studio package verification failed: "+str(error))
if "--verify-only" in sys.argv[1:]:
    print("SPIDER AUDIO STUDIO PACKAGE VERIFIED:",len(data["files"]),"files")
    raise SystemExit(0)

sys.path.insert(0,str(app))
try:
    from studio.main import main
except ImportError as error:
    raise SystemExit("Native Audio Studio requires Python3 + PyQt5/QtMultimedia: "+str(error))
main()
'''

def eligible(root):
    result=[]
    for dirname in ROOTS:
        place=root/dirname
        if place.is_symlink() or not place.is_dir():
            raise RuntimeError("Required native application source is missing: "+dirname)
        for parent,directories,files in os.walk(place,followlinks=False):
            directories[:]=sorted(d for d in directories
                                  if not d.startswith(".")
                                  and d!="__pycache__"
                                  and not (Path(parent)/d).is_symlink())
            for name in sorted(files):
                path=Path(parent)/name
                if path.suffix.lower() in ALLOW:
                    result.append(path)
    for name in INDIVIDUAL:
        result.append(root/name)
    paths={}
    total=0
    for item in result:
        if item.is_symlink() or not item.is_file():
            raise RuntimeError("Refusing linked/missing Studio source: "+str(item))
        if item.stat().st_size>MAX_ITEM:
            raise RuntimeError("Source file too large for the developer package")
        relative=item.relative_to(root).as_posix()
        if relative in paths:
            raise RuntimeError("Duplicate runtime source file")
        paths[relative]=item
        total+=item.stat().st_size
    if not 40<=len(paths)<=900 or total>MAX_TOTAL:
        raise RuntimeError("Studio developer runtime is incomplete or oversized")
    return paths

def build(output_dir, *, source=SOURCE):
    source=Path(source).resolve()
    chosen=eligible(source)
    output=Path(output_dir).expanduser()
    if output.is_symlink() or not output.is_dir():
        raise RuntimeError("Choose an existing, real output directory")
    target=output/(PACKAGE+".tar.gz")
    if target.is_symlink() or target.exists():
        raise FileExistsError("A Spider Audio Studio package already exists: "+str(target))
    with tempfile.TemporaryDirectory(prefix="spider-audio-package-") as work:
        bundle=Path(work)/PACKAGE
        app=bundle/"app"
        app.mkdir(parents=True)
        hashes={}
        for rel,path in sorted(chosen.items()):
            dest=app/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            with path.open("rb") as inp, dest.open("xb") as out:
                shutil.copyfileobj(inp,out)
            dest.chmod(0o644)
            hashes[rel]=hashlib.sha256(dest.read_bytes()).hexdigest()
        (bundle/"run_spider_audio_studio.py").write_text(LAUNCHER,encoding="utf-8")
        (bundle/"run_spider_audio_studio.py").chmod(0o755)
        revision="unknown"
        try:
            record=subprocess.run(
                ["git","-C",str(source),"rev-parse","HEAD"],
                capture_output=True,text=True,timeout=3,check=False)
            if record.returncode==0 and len(record.stdout.strip())==40:
                revision=record.stdout.strip()
        except (OSError,subprocess.TimeoutExpired):
            pass
        manifest={"schema":1,"app":"Spider Audio Studio",
                  "version":VERSION,"source_revision":revision,
                  "private_developer_preview":True,"files":hashes}
        (bundle/"manifest.json").write_text(
            json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        (bundle/"manifest.json").chmod(0o600)
        # The archive contains the original app sources and no user's music,
        # credentials, local SoundFont banks or model weights.
        fd,tmp=tempfile.mkstemp(
            prefix=".spider-audio-package-",suffix=".tar.gz",dir=str(output))
        try:
            os.close(fd)
            with tarfile.open(tmp,"w:gz") as tar:
                for item in sorted(bundle.rglob("*")):
                    if item.is_file():
                        tar.add(item,arcname=item.relative_to(bundle.parent).as_posix(),
                                recursive=False)
            os.chmod(tmp,0o600)
            if target.exists() or target.is_symlink():
                raise FileExistsError("Package filename became occupied")
            os.link(tmp,target,follow_symlinks=False)
        finally:
            Path(tmp).unlink(missing_ok=True)
    return target

def main(argv=None):
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output-dir",default=str(Path.home()/"Downloads"))
    args=cli.parse_args(argv)
    try:
        result=build(args.output_dir)
    except (OSError,RuntimeError,ValueError) as exc:
        cli.exit(2,"Spider Audio Studio bundling rejected: "+str(exc)+"\n")
    print("SPIDER AUDIO STUDIO STANDALONE SOURCE PACKAGE:",result)
    print("This is a separate developer preview, NOT installed OS software.")
    print("Review licenses and hardware dependencies before public redistribution.")

if __name__=="__main__":
    main()
