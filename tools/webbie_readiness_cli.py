#!/usr/bin/env python3
"""Read-only Spider OS Webbie readiness check for staged PC reconciliation.

No service starts/stops, microphone/camera capture, model download, password
access, repair, document scan, network activity (unless --local-ollama),
or changes to the owner's running installation. Safe to run from source.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
sys.path.insert(0,str(ROOT/"webbie/brain"))
from runtime_readiness import inspect_readiness, render_report
from voice_lab import inspect_voice_lab, voice_lab_report
from local_model_inventory import inspect_local_models, report_lines


def collect(*, models=False):
    checks=inspect_readiness()
    voice=inspect_voice_lab()
    result={
        "report_format":"webbie-safe-readiness-v1",
        "runtime":[{"component":row.key,"status":row.status,
                    "detail":row.detail} for row in checks],
        "voice":{
            "whisper_available":voice["whisper_available"],
            "model_available":voice["whisper_model_available"],
            "recorder_available":voice["arecord_available"],
            "speaker_provider_opted_in":voice["voiceprint_opted_in"],
            "speaker_provider_code_pinned":voice["voiceprint_source_pinned"],
            "speaker_identity_verified":False,
        },
        "warning":"SOURCE/STATUS PRESENCE ONLY; no microphone, speaker or deployment was tested.",
    }
    if models:
        info=inspect_local_models()
        # Only model tag availability and count, never messages or prompts.
        result["local_ollama"]={
            "responding":info["online"],
            "installed_model_count":len(info["installed"]),
            "currently_loaded_count":len(info["running"]),
        }
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json",action="store_true",
                        help="Emit sanitized, content-free JSON")
    parser.add_argument("--local-ollama",action="store_true",
                        help="Also check model tags on localhost only (no prompts)")
    args=parser.parse_args(argv)
    snapshot=collect(models=args.local_ollama)
    if args.json:
        print(json.dumps(snapshot,indent=2))
    else:
        print("WEBBIE READINESS · NO CHANGES TO SPIDER OS")
        for row in snapshot["runtime"]:
            print(f"{row['component']}: {row['status']} | {row['detail']}")
        voice=snapshot["voice"]
        print("Whisper installed: "+str(voice["whisper_available"]))
        print("Whisper model present: "+str(voice["model_available"]))
        print("ALSA recorder present: "+str(voice["recorder_available"]))
        print("Speaker code pinned: "+str(voice["speaker_provider_code_pinned"]))
        print("Speaker identity verified: False")
        if args.local_ollama:
            print("Local Ollama responding: "+str(
                snapshot["local_ollama"]["responding"]))
        print(snapshot["warning"])
    return 0


if __name__=="__main__":
    sys.exit(main())
