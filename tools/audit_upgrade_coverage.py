#!/usr/bin/env python3
"""Read-only source/installer coverage check for Spider OS native upgrades.

Checks that the named, already-developed modules are in this source snapshot
and are included by BOTH installed and live ISO payload staging. This is not
a functional test on the owner's installed PC, and doesn't inspect personal data.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Only files whose purpose was confirmed in the native repository are pinned.
SOURCE_AREAS = {
    "The Web and native immersive bays": (
        "the-web/shell/main.py", "the-web/shell/workspaces.py",
        "the-web/shell/immersive_bays.py",
        "the-web/shell/workspace_max_native.py",
        "the-web/shell/app_catalog.py",
        "spider_max_source/spider_monster/max_catalog.py",
    ),
    "Webbie resident AI and voice": (
        "webbie/agent/webbie.py", "webbie/voice/whisper_listener.py",
        "webbie/actions/gateway.py", "webbie/brain/brain.py",
        "the-web/shell/webbie_camera.py",
    ),
    "Native Spider Studio": (
        "studio/main.py", "studio/multitrack.py",
        "studio/production_board.py", "studio/session_qc.py",
        "studio/release_export.py", "studio/bin/studio",
    ),
    "Author and Broken World": (
        "author/main.py", "author/store.py",
        "author/continuity_engine.py", "author/master_canon.py",
        "author/story_atlas.py", "author/bin/author",
    ),
    "School / Study": (
        "study/study.py", "study/store.py",
        "study/apa.py", "study/dashboard.py", "study/bin/study",
    ),
    "Forage and Deep Forage": (
        "forage/forage.py", "forage/local_index.py",
        "forage/research_quality.py", "forage/deep-forage/deep_forage.py",
    ),
    "Kali Bay and evidence": (
        "kali-bay/ui/kali_bay.py",
        "kali-bay/runtime/evidence_ledger.py",
        "kali-bay/bin/kali-bay",
    ),
    "Spider Media Center bridge and Nova": (
        "media/bin/spider-media-center",
        "media/ai-dj/service.py", "media/ai-dj/nova_host.py",
        "system/apps.py",
    ),
    "System, backups and recovery": (
        "system/guardian.py", "system/vault.py",
        "system/release_batch.py", "system/release_readiness.py",
    ),
    "Approved workspace artwork": (
        "branding/wallpapers/collection.json",
        "branding/workspaces/studio.png",
        "branding/workspaces/kali-bay.png",
        "branding/workspaces/study.png",
    ),
}

ROOT_COMPONENTS = (
    "spider-core", "webbie", "forage", "the-web", "kali-bay",
    "study", "media", "system", "studio", "author", "spider_max_source",
)
IMMERSIVE = {
    "studio", "author", "study", "kali-bay",
    "media", "webbie", "deep-forage", "art-lab",
}
REQUIRED_DESKTOPS = ("webbie", "study", "forage", "deep-forage",
                     "kali-bay", "spider-guardian", "spider-vault",
                     "studio", "author")

# The approved 26.04 destination layout has 15 top-level workspaces.
# Recovery is a function inside System. These are planned states, not
# a license to delete existing Recovery/Games data or tabs prematurely.
TARGET_WORKSPACES = {
    "default", "study", "author", "studio", "media", "webbie",
    "forage", "deep-forage", "dev-bay", "art-lab",
    "communications", "productivity", "devices", "kali-bay", "system",
}


def audit(root: Path = ROOT) -> dict:
    root = root.resolve()
    missing = {}
    for name, paths in SOURCE_AREAS.items():
        absent = [p for p in paths if not (root / p).is_file()]
        if absent:
            missing[name] = absent
    iso_path = root / "distro/build-iso.sh"
    iso_source = iso_path.read_text(encoding="utf-8") if iso_path.is_file() else ""
    iso_gaps = []
    # Every source component must be staged into both installed and live layers.
    # The common loop covers the six non-primary components.
    for component in ROOT_COMPONENTS:
        literal = '${ROOT}/' + component + '/'
        staged = iso_source.count(literal) >= 2
        if not staged and component in (
            "study", "media", "system", "studio", "author", "spider_max_source"
        ):
            loop = "for component in study media system studio author spider_max_source; do"
            staged = iso_source.count(loop) >= 2
        if not staged:
            iso_gaps.append(component)
    if iso_source.count("branding/") < 2:
        iso_gaps.append("branding")
    for desktop in REQUIRED_DESKTOPS:
        if not (root / f"distro/config/applications/{desktop}.desktop").is_file():
            iso_gaps.append(f"desktop:{desktop}")
    scenes_file = root / "the-web/shell/immersive_bays.py"
    scenes = set()
    if scenes_file.is_file():
        tree = ast.parse(scenes_file.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SCENES" for t in node.targets
            ):
                scenes = set(ast.literal_eval(node.value).keys())
                break
    scene_gaps = sorted(IMMERSIVE - scenes)
    manifest = root / "distro/config/base.env"
    base = manifest.read_text() if manifest.is_file() else ""
    lts_pinned = all(entry in base for entry in (
        'UBUNTU_RELEASE="26.04"', 'UBUNTU_CODENAME="resolute"',
        'UBUNTU_IMAGE_VERSION="26.04.1"'
    ))
    # Check the actual The Web registry, not only mockups or docs.
    catalog_file = root / "the-web/shell/app_catalog.py"
    declared = set()
    if catalog_file.is_file():
        for node in ast.parse(catalog_file.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "WORKSPACES" for t in node.targets
            ):
                declared = set(ast.literal_eval(node.value))
                break
    outstanding_workspaces = sorted(TARGET_WORKSPACES - declared)
    legacy_top_level = sorted(({"recovery", "games"} & declared))
    media_install = root / "distro/install-spm.sh"
    media_source = media_install.read_text() if media_install.is_file() else ""
    # 'external required' is expected, not a passing install claim.
    external_media = ("CANDIDATES=" in media_source
                      and "ZIP=" in media_source)
    return {
        "base": "Ubuntu Studio 26.04.1 LTS build target",
        "base_config_pinned": lts_pinned,
        "source_areas": {k: "source present" if k not in missing
                         else "missing source" for k in SOURCE_AREAS},
        "missing_source": missing,
        "missing_iso_payload_components": iso_gaps,
        "missing_immersive_scenes": scene_gaps,
        "media_electron_binary": (
            "separate validated package required"
            if external_media else "media installer contract missing"
        ),
        "target_workspace_count": len(TARGET_WORKSPACES),
        "unimplemented_destination_workspaces": outstanding_workspaces,
        "legacy_top_level_workspaces_to_review": legacy_top_level,
        "actual_pc_synchronization": "unverified; local read-only audit required",
        "full_26_04_iso_build_and_vm_install": "not established by this check",
        "passes_source_coverage": bool(lts_pinned and not missing
                                     and not iso_gaps and not scene_gaps
                                     and external_media),
        # This flag deliberately stays false until the host/install/media gates
        # are separately verified. Green source CI cannot greenlight deployment.
        "ready_for_host_installation": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = audit(args.root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for key, value in report["source_areas"].items():
            print(f"{key}: {value}")
        for key in ("missing_source", "missing_iso_payload_components",
                    "missing_immersive_scenes"):
            if report[key]:
                print(f"FAIL {key}: {report[key]}")
        print("Media Center runtime:", report["media_electron_binary"])
        print("Missing destination bays:", report["unimplemented_destination_workspaces"])
        print("Legacy top-level bays:", report["legacy_top_level_workspaces_to_review"])
        print("Installed machine:", report["actual_pc_synchronization"])
        print("Result:", "SOURCE COVERAGE PASS" if report["passes_source_coverage"]
              else "SOURCE COVERAGE FAIL")
    return 0 if report["passes_source_coverage"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
