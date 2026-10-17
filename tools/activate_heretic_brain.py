#!/usr/bin/env python3
"""Finalize owner-requested Ollama Heretic install, using the existing Webbie.

This helper is called only by the explicitly launched Konsole installer.
Never accepts a model name or command from LLM/voice/browser content.
"""
import sys
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/"webbie"/"brain"))
from resident_model_choice import installed_models, select_installed_model

MODEL="hf.co/mradermacher/Qwen3-8B-heretic-GGUF:Q4_K_M"


def activate_prebuilt(model_list=None, *, path=None):
    available=tuple(installed_models() if model_list is None else model_list)
    names=[name for name in available if name.casefold()==MODEL.casefold()]
    if len(names)!=1:
        raise RuntimeError("The reviewed Heretic GGUF was not found in local Ollama; original Webbie unchanged")
    options={"owner_clicked":True, "available":available}
    if path is not None:
        options["path"]=path
    return select_installed_model(names[0],**options)


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    if argv!=["--owner-approved-install"]:
        print("Use the owner-confirmed Webbie Heretic installer, not a generated model command.",file=sys.stderr)
        return 2
    try:
        model=activate_prebuilt()
    except (RuntimeError,OSError,ValueError,PermissionError) as error:
        print("Heretic activation did not complete: "+str(error),file=sys.stderr)
        return 1
    print("WEBBIE EVERYDAY BRAIN SELECTED: "+model)
    print("Resident Webbie will use this model on subsequent full-brain replies.")
    print("Natasha, memory, native desktop tools and original Qwen3 remain intact.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
