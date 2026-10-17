"""Conservative commercial-distribution readiness gate for Spider Audio Studio.

This is NOT a software license evaluator or a substitute for counsel.
A passing beta build cannot implicitly authorize a public launch or sale.
When evidence is missing or ambiguous, report BLOCKED, not approval.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/"studio"/"product"/"commercial_release_evidence.json"
CHECKS={
    "owner_approved_business_model":"Explicit owner-approved distribution model and price",
    "pyqt5_distribution_rights":"GPL-compatible source compliance or documented commercial PyQt5 licensing",
    "qt_distribution_rights":"Correct Qt module licenses and LGPL/GPL or commercial obligations",
    "ffmpeg_redistribution":"FFmpeg build flags, source notices, codec/patent and packaging decisions",
    "asset_and_soundfont_rights":"Ownership or redistributable licenses for each bundled visual/audio/model asset",
    "source_license_review":"Legal review of the current MIT repo and all copyleft dependencies",
    "installer_security_review":"Independent safety/security check of packaging, updater and data preservation",
    "linux_hardware_acceptance":"Audio playback, recording, interface, MIDI and latency tests on supported Linux versions",
    "user_support_and_refunds":"Real support contact, support policy, sale and refund terms",
    "privacy_policy_and_telemetry":"Document actual privacy behavior and any future analytics or subscriptions",
    "accessibility_and_docs":"Accessible UX, installation/uninstall help and actual user acceptance results",
    "owner_approves_public_release":"Specific owner authorization to publish and sell the release",
}

def assess(path=EVIDENCE):
    blockers=[]
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,ValueError,UnicodeError):
        data={}
        blockers.append("Release evidence file is unreadable or missing.")
    if type(data) is not dict or data.get("schema")!=1:
        blockers.append("Unsupported release-evidence schema.")
        data={}
    model=data.get("distribution_model")
    if model not in ("gpl_compatible","proprietary_licensed"):
        blockers.append("Choose GPL-compatible open-source or properly licensed proprietary distribution.")
    assertions=data.get("checks")
    if type(assertions) is not dict:
        assertions={}
    for field,description in CHECKS.items():
        entry=assertions.get(field)
        if not isinstance(entry,dict) or entry.get("state")!="approved":
            blockers.append(description+" has not been approved.")
            continue
        evidence=entry.get("evidence")
        reviewer=entry.get("reviewer")
        if (not isinstance(evidence,str) or len(evidence.strip())<12 or
                not isinstance(reviewer,str) or len(reviewer.strip())<2):
            blockers.append(description+" lacks specific evidence and reviewer.")
    if model=="proprietary_licensed":
        # Never automatically infer paid PyQt rights from this MIT repository.
        if assertions.get("pyqt5_distribution_rights",{}).get("state")!="approved":
            blockers.append("MIT source plus stock GPL PyQt5 is NOT a proprietary license grant.")
    return {
        "product":"Spider Audio Studio",
        "commercial_distribution":("BLOCKED" if blockers else "DOCUMENTED_FOR_HUMAN_REVIEW"),
        "automated_legal_clearance":False,
        "distribution_model":model or "undecided",
        "blockers":blockers,
        "warning":("Evidence assertions are provided by people, not cryptographically validated. "
                   "Even when all fields are complete, professional license/security review "
                   "and an explicit owner-controlled release action are required."),
    }

def main(argv=None):
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--evidence",default=str(EVIDENCE))
    cli.add_argument("--assert-blocked",action="store_true",
                     help="For private beta CI: assert commercial release is still blocked.")
    opts=cli.parse_args(argv)
    result=assess(opts.evidence)
    print(json.dumps(result,indent=2,sort_keys=True))
    if opts.assert_blocked:
        return 0 if result["commercial_distribution"]=="BLOCKED" else 2
    # Even fully documented evidence needs external legal and owner go/no-go.
    return 2

if __name__=="__main__":
    raise SystemExit(main())
