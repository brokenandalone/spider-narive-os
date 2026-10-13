#!/usr/bin/env python3
"""Read-only gate for the consolidated Spider OS source and installed-PC review.

No cameras, credentials, documents, models, services, or user data are touched.
This deliberately DOES NOT offer an --apply option.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys

COMPONENTS = {
    "Webbie voice and context": (
        "webbie/agent/webbie.py", "webbie/agent/author_voice_bridge.py",
        "webbie/agent/kali_assistant.py", "webbie/agent/vision_query.py",
        "webbie/brain/brain.py", "webbie/brain/context_awareness.py",
        "webbie/brain/local_models.py", "webbie/voice/whisper_listener.py",
        "webbie/agent/voice_queue.py", "webbie/agent/proactive_checks.py",
        "webbie/agent/local_reminders.py", "webbie/agent/voice_supervisor.py",
        "webbie/agent/browser_routes.py", "webbie/brain/jarvis_context.py",
        "webbie/agent/voice_trust.py", "webbie/agent/runtime_readiness.py",
        "webbie/agent/segment_speaker_gate.py",
        "webbie/agent/speaker_provider_loader.py", "webbie/agent/voice_lab.py",
        "webbie/agent/launch_intents.py", "tools/webbie_readiness_cli.py",
        "webbie/agent/voice_metrics.py",
        "webbie/agent/kali_assistant.py",
        "webbie/agent/kali_named_app.py",
        "webbie/agent/console_bridge.py",
        "webbie/voice/hearing_test.py",
        "webbie/brain/focus_tasks.py", "webbie/brain/privacy_controls.py",
        "webbie/brain/model_resilience.py",
        "webbie/brain/unified_workflow.py",
        "webbie/brain/local_model_inventory.py",
    ),
    "Webbie vision and desktop": (
        "the-web/shell/webbie_camera.py", "the-web/shell/webbie_panel.py",
        "the-web/shell/webbie_vision_bridge.py",
        "the-web/shell/webbie_computer_panel.py",
        "the-web/shell/webbie_reminders_dialog.py",
        "the-web/shell/webbie_focus_dialog.py",
        "the-web/shell/webbie_cognitive_center.py",
        "the-web/shell/webbie_unified_workflow.py",
        "the-web/shell/webbie_jarvis_mission_center.py",
        "the-web/shell/main.py", "webbie/actions/autopilot_policy.py",
        "webbie/actions/navigation_missions.py", "webbie/actions/action_journal.py",
        "webbie/actions/action_receipts.py",
        "webbie/actions/owner_safe_access.py",
        "webbie/actions/owner_authorization_store.py",
        "webbie/actions/safe_service_status.py",
        "webbie/actions/jarvis_local_evidence.py",
        "webbie/actions/jarvis_site_audit.py",
        "webbie/actions/jarvis_orchestrator.py",
        "webbie/actions/jarvis_forage_research.py",
        "webbie/agent/workspace_launchers.py", "webbie/agent/jarvis_commands.py",
        "the-web/package/reconcile-native.py",
    ),
    "Study and school OneDrive": (
        "study/study.py", "study/school_portal.py", "study/homework_ui.py",
        "study/homework.py", "study/assignment_review.py",
        "study/course_materials.py", "study/draft_storage.py",
        "study/school_onedrive.py", "study/school_upload.py",
        "study/school_material_picker.py", "study/bin/webbie-homework",
    ),
    "Studio music and vocals": (
        "studio/__init__.py", "studio/main.py", "studio/ai_panel.py", "studio/music_backend.py",
        "studio/arrangement.py", "studio/voice_dataset.py",
        "studio/owner_voice_model.py", "studio/voice_conversion.py",
        "studio/song_mix.py", "studio/stem_separation.py",
        "studio/ai_controls.py", "studio/rvc_loopback.py",
        "studio/voice_profile.py", "studio/package/music-engine.sh",
        "studio/package/voice-engine.sh",
    ),
    "Author library and continuity": (
        "author/main.py", "author/web_features.py",
        "author/review_engine.py", "author/review_history.py",
        "author/voice_reader.py", "author/commands.py",
        "author/commands_client.py", "author/continuity_engine.py",
        "author/control_socket.py", "author/review_cache.py",
        "author/narration_bookmarks.py",
    ),
    "Kali Bay": (
        "kali-bay/ui/kali_bay.py", "kali-bay/bin/kali-bay",
        "kali-bay/runtime/kali_apps.py",
        "kali-bay/package/install-kali-bay.sh",
    ),
    "Nova and BCN Radio": (
        "media/ai-dj/service.py", "media/ai-dj/nova_host.py",
        "media/ai-dj/spider-ai-dj.service",
    ),
    "Forage": ("forage/engine.py",),
}

# Basic wiring checks. A file that exists but is never called is not installed
# functionality. These checks are deliberately conservative: passing them
# does NOT prove runtime success.
WIRING = {
    "webbie/agent/webbie.py": (
        "author_voice_bridge", "kali_assistant", "ask_vision",
        "parse_browser_command", "read_context",
        "ProactiveMonitor", "ReminderScheduler",
        "focus_answer", "private_session_active",
        "voice_permission", "inspect_readiness", "speaker_gate_from_config",
        "VOICE_INTAKE", "MODEL_GOVERNOR", "direct_launch_intent",
    ),
    "the-web/shell/webbie_panel.py": (
        "show_proactive_checks", "open_reminders_dialog",
        "publish_jarvis_context", "parse_browser_command",
        "parse_navigation_request", "open_cognitive_center", "stop_sensitive_actions", "last_action",
        "unified_workflow", "open_unified_workflow", "workflow_status",
        "enable_safe_access", "webbieOwnerOneClickAccess",
        "ConsoleWorker", "restore_standing_access", "remove_saved_permissions",
        "open_jarvis_mission_center"),
    "webbie/brain/brain.py": ("private_session_active", "remember_turn", "MODEL_GOVERNOR"),
    "the-web/shell/webbie_cognitive_center.py": ("set_private_session", "inspect_local_models", "inspect_readiness", "test_hearing", "open_workflow"),
    "webbie/brain/unified_workflow.py": ("observed_window", "record_action", "confirm_result"),
    "webbie/actions/task_grants.py": ("activate_wide", "select_wide_app"),
    "webbie/actions/owner_safe_access.py": ("authorize_service", "BLOCKED_ACTIONS", "restore_permanent", "web.open"),
    "webbie/actions/owner_authorization_store.py": ("update_policy", "read_policy", "kali_on_demand"),
    "webbie/agent/console_bridge.py": ("perform_console_request", "parse_console_request"),
    "webbie/agent/kali_named_app.py": ("launch_named_kali_app", "installed_apps"),
    "webbie/actions/jarvis_local_evidence.py": ("search_local_evidence", "approved_root"),
    "webbie/actions/jarvis_site_audit.py": ("inspect_site_project", "missing_local_assets"),
    "webbie/actions/jarvis_orchestrator.py": ("JarvisCore", "MissionResult", "source"),
    "webbie/actions/jarvis_forage_research.py": ("research_public_web", "render_public_research"),
    "the-web/shell/webbie_jarvis_mission_center.py": ("JarvisMissionCenter", "JarvisMissionWorker"),
    "the-web/shell/webbie_computer_panel.py": ("authorize_wide_access", "inspect_safe_services"),
    "webbie/agent/speaker_provider_loader.py": ("provider_sha256", "_pinned_source"),
    "study/study.py": ("open_homework", "open_school_onedrive"),
    "studio/main.py": ("StudioAIPanel",),
    "author/main.py": ("AuthorToolkit", "AuthorCommandServer"),
    "webbie/voice/whisper_listener.py": ("verifier", "capture_indicator_start"),
    "the-web/shell/webbie_camera.py": ("qwen3-vl:2b-instruct", "mjpeg", "640x480"),
}
SENSITIVE_PC_FILES = (
    "webbie/agent/webbie.py", "webbie/brain/brain.py",
    "webbie/voice/whisper_listener.py", "the-web/shell/webbie_panel.py",
    "the-web/shell/webbie_camera.py", "author/main.py", "study/study.py",
    "studio/main.py", "kali-bay/ui/kali_bay.py", "media/ai-dj/service.py",
)


def release_manifest(root: Path) -> set[str]:
    source = root / "system/release_batch.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_FILES"
            for target in statement.targets
        ):
            values = ast.literal_eval(statement.value)
            if not isinstance(values, (tuple, list)) or not all(
                isinstance(path, str) for path in values
            ):
                raise ValueError("Unexpected APP_FILES manifest format")
            return set(values)
    raise ValueError("No static APP_FILES manifest found")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            result.update(block)
    return result.hexdigest()


def audit(root: Path, installed: Path) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    notes: list[str] = []
    root = Path(root).resolve()
    installed = Path(installed)
    required = set()
    for group, paths in COMPONENTS.items():
        missing = []
        for relative in paths:
            required.add(relative)
            source = root / relative
            if source.is_symlink() or not source.is_file():
                missing.append(relative)
            elif relative.endswith(".py"):
                try:
                    ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
                except (SyntaxError, ValueError, UnicodeError, OSError):
                    blockers.append("INVALID PYTHON: " + relative)
        if missing:
            blockers.extend("MISSING SOURCE: " + path for path in missing)
        else:
            notes.append("SOURCE PRESENT: " + group)
    try:
        manifest = release_manifest(root)
        blockers.extend(
            "NOT IN BATCH INSTALLER: " + relative
            for relative in sorted(required - manifest)
        )
    except (SyntaxError, ValueError, OSError) as error:
        blockers.append("BATCH MANIFEST UNREADABLE: " + type(error).__name__)
    for relative, markers in WIRING.items():
        source = root / relative
        if not source.is_file() or source.is_symlink():
            continue
        try:
            content = source.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        for marker in markers:
            if marker not in content:
                blockers.append("ENTRYPOINT NOT WIRED: " + relative + " -> " + marker)
    for relative in SENSITIVE_PC_FILES:
        source, live = root / relative, installed / relative
        if live.is_symlink():
            blockers.append("PC SYMLINK NEEDS REVIEW: " + relative)
        elif not live.is_file():
            notes.append("PC NOT PRESENT: " + relative)
        elif source.is_file() and not source.is_symlink():
            if digest(source) != digest(live):
                notes.append("PC DIFFERS (PRESERVE AND RECONCILE): " + relative)
            else:
                notes.append("PC MATCHES: " + relative)
    return blockers, notes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root", type=Path,
                        default=Path("/usr/local/lib/spider-os"))
    args = parser.parse_args(argv)
    if args.checkout.resolve() == args.installed_root.resolve():
        parser.error("Audit a separate Git checkout, not the installed source tree.")
    blockers, notes = audit(args.checkout, args.installed_root)
    for line in notes:
        print(line)
    for line in blockers:
        print("BLOCKED: " + line)
    print("SOURCE RELEASE GATE: " +
          ("BLOCKED" if blockers else "SOURCE READY; PC REVIEW STILL REQUIRED"))
    print("This command did not install, replace, or restart anything.")
    return 3 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
