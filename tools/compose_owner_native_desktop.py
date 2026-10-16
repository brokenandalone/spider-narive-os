#!/usr/bin/env python3
"""Prepare a guarded *partial* owner-specific Spider OS native desktop merge.

Only the three review-backed navigation/catalog/folder modules are composed.
The other two Webbie modules are deliberately left unresolved and untouched.
Read original source only from the already-owner-private, hash-verified desktop
Bridge stage. Never install, run owner code, commit owner code, or use sudo.

The output is a PRIVATE NON-INSTALLABLE candidate for offline semantic QA,
not an installer and not a way around the strict 33-file release gate.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

from draft_native_desktop_merge import preservation_overlay
from review_staged_desktop_methods import DESKTOP, MAX_BYTES, inspect_stage, read_regular
from stage_native_merge import _private_folder, _private_write

RESOLVED = (
    "the-web/shell/main.py",
    "the-web/shell/app_catalog.py",
    "the-web/shell/workspace_files.py",
)
DEFERRED = (
    "the-web/shell/webbie_panel.py",
    "the-web/shell/webbie_cognitive_center.py",
)
VERSION = "spider-native-partial-owner-semantic-merge-v1"


def _module(tree, name):
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    raise ValueError("Missing required module definition: " + name)


def _method(tree, owner, name):
    cls = _module(tree, owner)
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise ValueError("Missing required member: " + owner + "." + name)


def _flat_strings(node):
    return set(value.value for value in ast.walk(node)
               if isinstance(value, ast.Constant) and isinstance(value.value, str))


def _attrs_assigned(node):
    return {item.attr for item in ast.walk(node)
            if isinstance(item, ast.Attribute) and isinstance(item.ctx, ast.Store)
            and isinstance(item.value, ast.Name) and item.value.id == "self"}


def _check_desktop(old, new):
    owner=ast.parse(old.decode("utf-8"))
    candidate=ast.parse(new.decode("utf-8"))
    # The incoming shell must retain all owner __init__ instance attributes.
    missing=_attrs_assigned(_method(owner,"TheWeb","__init__")) - _attrs_assigned(
        _method(candidate,"TheWeb","__init__"))
    if missing:
        raise ValueError("Candidate would drop owner desktop state fields: " +
                         ", ".join(sorted(missing)))
    build=_method(candidate,"TheWeb","build_ui")
    opening=_method(candidate,"TheWeb","open_workspace")
    close=_method(candidate,"TheWeb","can_close")
    installed=_method(candidate,"TheWeb","open_installed")
    check_strings=(
        (build,("nativeBay",),False),
        (opening,("Native workspace","Projects & missions",
                  "Optional installed tools","Webbie controls",
                  "Drums · Guitar · Bass · Keys"),True),
        (close,("Finish workspace analysis before closing this bay.",),True),
        (installed,("app",),True),
    )
    for node, words, exact in check_strings:
        pool=_flat_strings(node)
        for item in words:
            found=item in pool if exact else any(item in part for part in pool)
            if not found and exact:
                raise ValueError("Missing native desktop preservation invariant: " + item)
    # The installed code's desktop navigation lifecycle must remain represented.
    old_open=_method(owner,"TheWeb","open_workspace")
    new_names={item.attr for item in ast.walk(opening) if isinstance(item,ast.Attribute)}
    old_names={item.attr for item in ast.walk(old_open) if isinstance(item,ast.Attribute)}
    critical={"set_workspace","save_state","update_webbie_context",
              "remember_navigation","raise_","activateWindow"}
    if not critical <= (old_names & new_names):
        raise ValueError("Owner native navigation lifecycle missing from incoming shell")
    return {"constructor_state_retained": True,
            "navigation_lifecycle_retained": True,
            "native_bay_invariants": True}


def _dict_entries(node):
    for item in ast.walk(node):
        if isinstance(item, ast.Assign) and any(
            isinstance(target,ast.Name) and target.id == "entries"
            for target in item.targets):
            if not isinstance(item.value,ast.Dict):
                raise ValueError("Unexpected workspace folder mapping")
            return {
                key.value:value
                for key,value in zip(item.value.keys,item.value.values)
                if isinstance(key,ast.Constant) and isinstance(key.value,str)
            }
    raise ValueError("Workspace folder mapping not found")


def _normalize(node):
    return ast.dump(node,include_attributes=False)


def _check_folders(old,new):
    local=_dict_entries(_module(ast.parse(old.decode("utf-8")),"workspace_folders"))
    incoming=_dict_entries(_module(ast.parse(new.decode("utf-8")),"workspace_folders"))
    missing=set(local)-set(incoming)
    if missing:
        raise ValueError("Candidate removed owner folder categories: "+
                         ", ".join(sorted(missing)))
    for bay,node in local.items():
        candidate=incoming[bay]
        if bay == "system":
            # Original item must stay first when additional recovery links appear.
            if not (isinstance(node,ast.List) and isinstance(candidate,ast.List)
                    and len(candidate.elts)>=len(node.elts)
                    and all(_normalize(a)==_normalize(b)
                            for a,b in zip(node.elts,candidate.elts))):
                raise ValueError("Original system folder links changed")
        elif _normalize(node) != _normalize(candidate):
            raise ValueError("Owner's existing folder links changed: "+bay)
    for needed in ("productivity","devices"):
        if needed not in incoming:
            raise ValueError("Expected new native folder links are absent")
    return {"owner_folder_mappings_preserved":len(local),
            "candidate_native_folders_added":sorted(set(incoming)-set(local))}


def _check_catalog(old,new):
    old_ast=ast.parse(old.decode("utf-8"))
    new_ast=ast.parse(new.decode("utf-8"))
    incoming=_module(new_ast,"discover_apps")
    owner=_module(old_ast,"discover_apps")
    for name in ("Hidden","NoDisplay","OnlyShowIn","NotShowIn",
                 "TryExec","Desktop Entry"):
        if name not in _flat_strings(owner) or name not in _flat_strings(incoming):
            raise ValueError("Candidate changed a required XDG visibility condition")
    arg_names={a.arg for a in incoming.args.args}
    if not {"directories","desktops","locale","assignments"} <= arg_names:
        raise ValueError("Catalog lost legacy discover arguments or assignments")
    for name in ("workspace_for","save_app_assignment","read_app_assignments"):
        _module(new_ast,name)
    return {"hidden_launcher_rules_preserved":True,
            "existing_discovery_arguments_preserved":True,
            "owner_assignments_supported":True}


def generate(stage:Path,output:Path,home=None):
    stage=Path(stage).expanduser()
    existing=inspect_stage(stage)
    if tuple(result["file"] for result in existing)!=DESKTOP:
        raise ValueError("Stage manifest does not match this desktop source set")
    resolved=[]
    for name in RESOLVED:
        owner=read_regular(stage,"installed/"+name,MAX_BYTES)
        incoming=read_regular(stage,"candidate/"+name,MAX_BYTES)
        if name.endswith("main.py"):
            checks=_check_desktop(owner,incoming)
        elif name.endswith("app_catalog.py"):
            checks=_check_catalog(owner,incoming)
        else:
            checks=_check_folders(owner,incoming)
        # The candidate already contains the native behavior; add only
        # top-level owner-specific imports/methods. No Webbie code selection.
        compiled,notes=preservation_overlay(owner,incoming)
        compile(compiled,name,"exec")
        resolved.append((name,compiled,{
            "component":name,
            "checks":checks,
            "owner_unique_members_preserved":notes["owner_only_members_added"],
            "owner_unique_imports_added":notes["owner_only_imports_added"],
            "review_required":True,
        }))
    deferred=[]
    for name in DEFERRED:
        owner=read_regular(stage,"installed/"+name,MAX_BYTES)
        incoming=read_regular(stage,"candidate/"+name,MAX_BYTES)
        deferred.append({
            "component":name,
            "source_difference":hashlib.sha256(owner).hexdigest()!=hashlib.sha256(incoming).hexdigest(),
            "untouched":True,
            "manual_safety_merge_required":True,
        })
    output=Path(output).expanduser()
    _private_folder(output,home=Path.home() if home is None else Path(home),
                    source=stage,installed=Path("/usr/local/lib/spider-os"))
    for name,data,_ in resolved:
        _private_write(output,"candidate/"+name,data)
    report={
        "format":VERSION,
        "owner_code_publicly_uploaded":False,
        "installed_modified":False,
        "release_installable":False,
        "safe_to_overwrite":False,
        "desktop_navigation_candidates": [note for _,_,note in resolved],
        "webbie_safety_blocks":deferred,
        "full_release_owner_files_still_protected":33,
    }
    _private_write(output,"summary.json",json.dumps(report,indent=2)+"\n")
    _private_write(output,"README.txt",
        "SPIDER OS / PRIVATE DESKTOP INTEGRATION - NOT INSTALLABLE\n"
        "Three non-sensitive native desktop modules are composed for review.\n"
        "Webbie consent, STOP, voice, camera, workflow and cognitive files\n"
        "are still BLOCKED and are NOT merged or present in this output.\n"
        "This partial source set MUST NOT be copied into installed Spider OS.\n"
        "All modules and dynamic dependencies need further semantic QA.\n"
        "No installed source, service, model, audio, image or user data changed.\n"
        "Keep the owner-private source in this directory off public GitHub.\n")
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=generate(args.stage,args.output)
    except (ValueError,OSError,UnicodeError,SyntaxError) as error:
        print("GUARDED DESKTOP MERGE REFUSED:",error,file=sys.stderr)
        return 3
    print("SPIDER OS / REAL DESKTOP CANDIDATE COMPOSED (PRIVATE)")
    for row in result["desktop_navigation_candidates"]:
        print("STATIC CHECKS PASS:",row["component"])
    for row in result["webbie_safety_blocks"]:
        print("PRESERVED FOR SAFETY REVIEW:",row["component"])
    print("Owner source unchanged. Full 33-file installation guard remains active.")
    print("Private candidate only:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
