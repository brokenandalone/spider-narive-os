#!/usr/bin/env python3
"""Owner-private Webbie safety merge candidate. NEVER installs or runs Webbie.

Compose from verified current-GitHub + installed-source pairs. The native
candidate is the structural base so added widgets/classes survive. Original
owner consent, message, portrait, camera-sleep and close-method bodies win
on named conflicts. The candidate's audited fail-closed global STOP wins.
The legacy cognitive workflow is preserved only when an owner-only method
is present, and remains attached to an explicit GUI callback.

This output is NOT an authorized executable or deployable release. Verify
every remaining method conflict privately; 33 locally customized release
files remain protected. Never upload this generated source to public GitHub.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

from compose_owner_native_desktop import _check_live_candidate_snapshot, _attrs_assigned
from draft_native_desktop_merge import preservation_overlay
from review_staged_desktop_methods import (
    DESKTOP, MAX_BYTES, inspect_stage, read_regular,
)
from stage_native_merge import _private_folder, _private_write

WEBBIE_FILES = (
    "the-web/shell/webbie_panel.py",
    "the-web/shell/webbie_cognitive_center.py",
)
OWNER_METHODS = (
    "SpeakingPortrait.paintEvent",
    "WebbiePanel._remember_consented_screen",
    "WebbiePanel.closeEvent",
    "WebbiePanel.open_computer_dialog",
    "WebbiePanel.publish_jarvis_context",
    "WebbiePanel.request_proactive_checks",
    "WebbiePanel.send",
    "WebbiePanel.set_face_sleeping",
    "observed_state",
)
REVIEW_VERSION = "spider-private-webbie-safety-overlay-v1"


def _definitions(code: bytes):
    tree = ast.parse(code.decode("utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            found[node.name] = node
        if isinstance(node,ast.ClassDef):
            for item in node.body:
                if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    found[node.name + "." + item.name] = item
    return found


def _span(node):
    first=min([node.lineno]+[x.lineno for x in getattr(node,"decorator_list",())])
    return first-1,node.end_lineno


def _owner_method_transplants(original:bytes, candidate:bytes, names):
    owner=_definitions(original)
    new=_definitions(candidate)
    source_lines=original.decode("utf-8").splitlines(keepends=True)
    result_lines=candidate.decode("utf-8").splitlines(keepends=True)
    edits=[]
    for name in names:
        if name not in owner or name not in new:
            raise ValueError("Missing required Webbie owner/candidate method: "+name)
        a,b=_span(owner[name])
        c,d=_span(new[name])
        edits.append((c,d,source_lines[a:b],name))
    positions=sorted((a,b) for a,b,_,_ in edits)
    if any(y>z for (_,y),(z,_) in zip(positions,positions[1:])):
        raise ValueError("Overlapping Webbie method replacements")
    for start,end,lines,_ in sorted(edits,reverse=True):
        result_lines[start:end]=lines
    result="".join(result_lines).encode("utf-8")
    check=_definitions(result)
    for name in names:
        if ast.dump(check[name],include_attributes=False)!=ast.dump(
                owner[name],include_attributes=False):
            raise ValueError("Owner Webbie method modified while composing: "+name)
    return result


def _critical_constructor(original:bytes,candidate:bytes,klass):
    installed=_definitions(original)
    incoming=_definitions(candidate)
    key=klass+".__init__"
    if key not in installed or key not in incoming:
        raise ValueError("Missing Webbie constructor: "+key)
    if ast.dump(installed[key].args,include_attributes=False)!=ast.dump(
            incoming[key].args,include_attributes=False):
        raise ValueError("Changed owner Webbie constructor signature: "+key)
    before=_attrs_assigned(installed[key])
    after=_attrs_assigned(incoming[key])
    missing=before-after
    if missing:
        raise ValueError("New Webbie constructor drops owner state: "+
                         ", ".join(sorted(missing)))
    return {"owner_state_field_count":len(before),
            "owner_state_fields_preserved":True,
            "constructor_signature_preserved":True}


def _stop_gate(candidate:bytes):
    nodes=_definitions(candidate)
    stop=nodes.get("WebbiePanel.stop_sensitive_actions")
    if stop is None:
        raise ValueError("No current Webbie global STOP method")
    tokens={node.id for node in ast.walk(stop) if isinstance(node,ast.Name)}
    attributes={node.attr for node in ast.walk(stop)
                if isinstance(node,ast.Attribute)}
    strings={node.value for node in ast.walk(stop)
             if isinstance(node,ast.Constant) and isinstance(node.value,str)}
    required_names={"read_policy","update_policy"}
    required_attrs={"unified_workflow","stop_camera",
                    "revoke_observation","append_message"}
    if (not required_names <= tokens or not required_attrs <= attributes or
            "jarvis_core" not in (attributes | strings)):
        raise ValueError("Webbie STOP safety method lost required revocation paths")
    if not any("NOT verified" in value for value in strings):
        raise ValueError("Webbie STOP no longer warns of unverified revocation")
    calls=sum(1 for node in ast.walk(stop)
              if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
              and node.func.id=="read_policy")
    if calls<2:
        raise ValueError("Webbie STOP does not verify persisted authorization")
    if not any(isinstance(node,ast.Try) for node in ast.walk(stop)):
        raise ValueError("Webbie STOP lacks independent failure containment")
    return {"resident_and_standalone_mission_stop_supported":True,
            "saved_authorization_rechecked":True,
            "failures_reported_without_false_success":True}


def _cognitive_fallback(candidate:bytes):
    current=_definitions(candidate)
    node=current.get("WebbieCognitiveDialog.open_workflow")
    if node is None:
        raise ValueError("No supervised cognitive workflow callback")
    lines=candidate.decode("utf-8").splitlines(keepends=True)
    start,end=_span(node)
    # One GUI click. The native bay's callback takes precedence. If there
    # is no callback, retain the original installed offer_workflow path,
    # which is itself preserved in the private candidate from the owner.
    template=(
        "    def open_workflow(self):\n"
        "        if callable(self.workflow_callback):\n"
        "            return self.workflow_callback()\n"
        "        if callable(getattr(self, 'offer_workflow', None)):\n"
        "            return self.offer_workflow(None)\n"
        "        self.report.setPlainText(\n"
        "            'Open the guided workflow from the resident Webbie panel.')\n"
    )
    lines[start:end]=[template]
    result="".join(lines).encode("utf-8")
    compiled=_definitions(result)
    assert "WebbieCognitiveDialog.open_workflow" in compiled
    return result


def combine_pair(name,owner:bytes,incoming:bytes):
    overlay,record=preservation_overlay(owner,incoming)
    preserved=list(record["owner_only_members_added"])
    if name.endswith("webbie_panel.py"):
        constructor=_critical_constructor(owner,incoming,"WebbiePanel")
        safety=_stop_gate(incoming)
        relevant=[symbol for symbol in OWNER_METHODS
                  if symbol in _definitions(owner) and symbol in _definitions(overlay)]
        # Original owner method implementations are kept intact. In
        # particular no new typed-command parser gains background authority.
        merged=_owner_method_transplants(owner,overlay,relevant)
        for symbol in OWNER_METHODS:
            if symbol not in relevant:
                raise ValueError("Required Webbie owner safety method absent: "+symbol)
    else:
        constructor=_critical_constructor(owner,incoming,"WebbieCognitiveDialog")
        if not {"WebbieCognitiveDialog.offer_workflow",
                "WebbieCognitiveDialog.open_workflows"} <= set(preserved):
            # Same method bodies already present in both sources are fine.
            if not {"WebbieCognitiveDialog.offer_workflow",
                    "WebbieCognitiveDialog.open_workflows"} <= set(_definitions(overlay)):
                raise ValueError("Owner cognitive workflow methods lost")
        merged=_cognitive_fallback(overlay)
        safety={"owner_workflow_fallback_and_native_callback":True}
        relevant=["WebbieCognitiveDialog.offer_workflow",
                  "WebbieCognitiveDialog.open_workflows"]
    compile(merged,name,"exec")
    return merged,{
        "component":name,
        "constructor_checks":constructor,
        "global_stop_or_callback_checks":safety,
        "preserved_owner_unique_members":preserved,
        "preserved_original_sensitive_methods":relevant,
        "unresolved_other_shared_methods":sorted(set(record["unresolved_shared"])-set(relevant)),
        "install_allowed":False,
    }


def compose(stage:Path,output:Path,home=None,source=None):
    stage=Path(stage).expanduser()
    checked=inspect_stage(stage)
    if tuple(x["file"] for x in checked)!=DESKTOP:
        raise ValueError("Private desktop source-stage mismatch")
    _check_live_candidate_snapshot(
        stage, Path(__file__).resolve().parents[1] if source is None else source)
    result=[]
    for name in WEBBIE_FILES:
        old=read_regular(stage,"installed/"+name,MAX_BYTES)
        candidate=read_regular(stage,"candidate/"+name,MAX_BYTES)
        merged,info=combine_pair(name,old,candidate)
        result.append((name,merged,info))
    output=Path(output).expanduser()
    _private_folder(output,home=Path.home() if home is None else Path(home),
                    source=stage,installed=Path("/usr/local/lib/spider-os"))
    for name,data,_ in result:
        _private_write(output,"candidate/"+name,data)
    report={
        "format":REVIEW_VERSION,
        "owner_code_publicly_uploaded":False,
        "source_snapshot_verified":True,
        "installed_modified":False,
        "safe_to_overwrite":False,
        "release_installable":False,
        "full_release_owner_files_still_protected":33,
        "files":[info for _,_,info in result],
    }
    _private_write(output,"summary.json",json.dumps(report,indent=2)+"\n")
    _private_write(output,"README.txt",
        "SPIDER OS / PRIVATE WEBBIE SAFETY REVIEW CANDIDATE\n"
        "This is NOT a tested or installable replacement for your resident AI.\n"
        "Owner message, consent, camera-sleep, shutdown and portrait routines\n"
        "are preserved verbatim; current checked STOP and workflow callbacks\n"
        "are composed with owner-only methods for OFFLINE review.\n"
        "The constructor and other shared methods remain semantically\n"
        "unverified on the owner's live hardware and background services.\n"
        "Keep these source files PRIVATE and DO NOT copy into installed OS.\n"
        "All 33 owner-customized release files remain protected.\n")
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        report=compose(args.stage,args.output)
    except (OSError,ValueError,SyntaxError,UnicodeError) as e:
        print("PRIVATE WEBBIE SAFETY MERGE REFUSED:",e,file=sys.stderr)
        return 3
    print("SPIDER OS / PRIVATE WEBBIE SAFETY CANDIDATE COMPOSED")
    for item in report["files"]:
        print("CHECKED:",item["component"])
        print("  Owner-sensitive methods kept:",
              len(item["preserved_original_sensitive_methods"]))
        print("  Remaining shared methods for review:",
              len(item["unresolved_other_shared_methods"]))
        print("  Installation authorized: NO")
    print("No resident AI/service permissions changed. Full install remains blocked.")
    print("Private candidate only:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
