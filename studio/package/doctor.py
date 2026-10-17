"""Preflight for the packaged original Spider Audio Studio runtime.

Runs without opening microphone, DAW engine, SoundFont bank, or Webbie/Nova.
This is a dependency report, not proof of real audio hardware suitability.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import sys

REQUIRED_QT=("PyQt5.QtCore","PyQt5.QtWidgets","PyQt5.QtSvg","PyQt5.QtMultimedia")

def _module_present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError,ModuleNotFoundError,AttributeError,ValueError):
        return False

def report():
    components={
        "linux_desktop":sys.platform.startswith("linux"),
        "python_3_10_or_newer":sys.version_info >=(3,10),
        "required_pyqt5_modules":{
            name:_module_present(name) for name in REQUIRED_QT},
        "recommended_executables":{
            name:bool(shutil.which(name))
            for name in ("ffmpeg","ffprobe","fluidsynth","xdg-open")},
        "notes":[
            "FFmpeg is required for final offline multitrack WAV renders.",
            "FluidSynth and separately licensed SoundFonts are used by compatible virtual-band tools.",
            "No external audio interfaces or microphones were opened.",
            "QtMultimedia import does not guarantee functional sound output.",
            "No application files or audio recordings were changed."],
    }
    components["required_ready"]=(
        components["linux_desktop"]
        and components["python_3_10_or_newer"]
        and all(components["required_pyqt5_modules"].values()))
    return components

def main():
    info=report()
    print("SPIDER AUDIO STUDIO • LOCAL DEPENDENCY CHECK")
    print(json.dumps(info,indent=2,sort_keys=True))
    print("Application can start" if info["required_ready"]
          else "Missing a required desktop runtime dependency")
    return 0 if info["required_ready"] else 2

if __name__=="__main__":
    raise SystemExit(main())
