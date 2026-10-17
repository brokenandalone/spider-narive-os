"""Spider OS native-feature adoption policy.

A read-only prioritizer used inside the existing Dev Bay. It does not fetch,
install, run, enable, or approve any operating-system capability. A proposed
feature is never an installation authorization, even if its gates are marked.
"""
from __future__ import annotations

from dataclasses import dataclass

MODES = frozenset({"source", "supported_api", "isolated_trial", "release_upgrade"})
CORE_GATES = (
    "source_compatibility",
    "existing_bay_integration",
    "regression_tests",
    "owner_customizations_reconciled",
    "backup_and_rollback",
    "installed_host_acceptance",
)


@dataclass(frozen=True)
class Idea:
    key: str
    title: str
    bay: str
    benefit: int
    effort: int
    risk: int
    mode: str
    target: str
    source: str
    extra_gates: tuple[str, ...] = ()
    reuses_existing: bool = True


# One registry for existing bays; these are suggestions, not deployed features.
IDEAS = (
    Idea("native-handoff", "Real project and window handoffs", "Home / All Bays",
         5, 2, 2, "source", "Existing The Web and shared bay missions",
         "https://develop.kde.org/docs/plasma/kwin/"),
    Idea("project-search", "Shared private full-text project search", "Forage / Study / Author",
         5, 2, 2, "source", "Existing bay files with SQLite FTS5",
         "https://www.sqlite.org/fts5.html", ("private_search_scope",)),
    Idea("recovery-status", "Verified backups and rollback visibility", "System / Recovery",
         5, 3, 3, "supported_api", "Existing system health and release tools",
         "https://restic.readthedocs.io/en/stable/",
         ("independent_backup_proven",)),
    Idea("kwin-wayland", "KWin and Wayland-native workspace control", "The Web / Home",
         5, 4, 4, "supported_api", "Existing The Web desktop, not a replacement shell",
         "https://develop.kde.org/docs/plasma/kwin/",
         ("wayland_screen_and_window_parity",)),
    Idea("spider-eye-parity", "Spider Eye native desktop observation", "System / Devices",
         5, 4, 4, "supported_api", "Existing Spider Eye, preserve God's Eye until parity",
         "https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html",
         ("explicit_screen_consent", "gods_eye_feature_parity")),
    Idea("kde-connect", "Existing KDE Connect device integration", "Devices",
         4, 2, 2, "supported_api", "Existing Devices native panel",
         "https://apps.kde.org/kdeconnect/", ("user_approved_pairing",)),
    Idea("study-citations", "Study research and citation handoff", "Study",
         4, 2, 2, "supported_api", "Existing Study bay and user-selected Zotero library",
         "https://www.zotero.org/support/dev/web_api/v3/local_api",
         ("study_library_permission",)),
    Idea("media-broadcast-status", "Native BCN/Nova broadcast status", "Media Center",
         4, 2, 2, "supported_api", "Existing radio status service, no new station instance",
         "https://liquidsoap.readthedocs.io/",
         ("broadcast_no_interruption",)),
    Idea("immersive-scenes", "Interactive native immersive bay scenes", "Author / Art Lab",
         5, 5, 3, "isolated_trial", "Existing immersive_bays module and approved assets",
         "https://doc.qt.io/qt-6/qtquick3d-index.html",
         ("pyqt5_qt6_boundary_review", "gpu_cpu_budget_verified")),
    # Distro-inspired capabilities are adopted into existing bays, never
    # bundled wholesale from another distribution or package ecosystem.
    Idea("ubuntustudio-audio-2610",
         "26.10-style unified PipeWire controls and clear device status",
         "System / Studio integration", 5, 2, 3, "supported_api",
         "Existing System and Studio bays; read current audio graph first",
         "https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/",
         ("audio_device_baseline", "broadcast_no_interruption")),
    Idea("ubuntustudio-app-selection-2610",
         "Per-application creative-tool choices without bundled installs",
         "System / Dev Bay", 4, 2, 1, "source",
         "Existing installed-application catalog and optional-tools view",
         "https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/",
         ("installed_ubuntu_studio_apps_preserved",)),
    Idea("ubuntustudio-livecode-2610",
         "Optional Sonic Pi, SuperCollider and JNoise handoff",
         "Studio integration", 4, 2, 2, "supported_api",
         "Existing Studio workspace; separate audio engine unchanged",
         "https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/",
         ("approved_optional_packages_only", "audio_device_baseline")),
    Idea("ubuntustudio-creative-suite-2610",
         "Compatible modern Krita, GIMP, Kdenlive and Ardour project handoff",
         "Art Lab / Media / Studio integration", 4, 3, 3, "supported_api",
         "Existing professional applications and project formats",
         "https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/",
         ("installed_ubuntu_studio_apps_preserved", "project_roundtrip_verified")),
    Idea("ubuntu-2610-system-audit",
         "26.10 kernel, systemd, OpenSSL and core-tool migration checks",
         "System / Dev Bay", 5, 3, 2, "source",
         "Existing read-only release readiness and test suites",
         "https://documentation.ubuntu.com/release-notes/26.10/",
         ("legacy_init_services_audited", "openssl4_compatibility_audited",
          "core_utility_semantics_verified")),
    Idea("opensuse-update-batches",
         "openQA-style cross-component acceptance before upgrade",
         "System / Dev Bay", 5, 2, 2, "source",
         "Existing GitHub release tests and hardware acceptance gates",
         "https://doc.opensuse.org/documentation/tumbleweed/updating_upgrading_reverting/",
         ("existing_services_preserved",)),
    Idea("opensuse-rollback-design",
         "Clear update checkpoints and verified restoration",
         "System / Recovery", 5, 2, 2, "source",
         "Existing Spider OS backup, manifest and rollback transaction",
         "https://manpages.opensuse.org/Tumbleweed/transactional-update/transactional-update.8.en.html",
         ("ext4_btrfs_strategy_isolated", "independent_backup_proven")),
    Idea("fedora-atomic-release-principles",
         "Versioned, auditable releases with separate owner data",
         "System / Recovery", 5, 2, 2, "source",
         "Existing release_batch transaction; no rpm-ostree migration",
         "https://coreos.github.io/rpm-ostree/administrator-handbook/",
         ("rollback_manifest_verified",)),
    Idea("nixos-declarative-inventory",
         "Reproducible manifest of bays, packages and services",
         "System / Dev Bay", 5, 2, 2, "source",
         "Existing native release manifest, owner-private inventories",
         "https://wiki.nixos.org/wiki/Overview_of_the_NixOS_Linux_distribution",
         ("private_configuration_not_published",)),
    Idea("cosmic-native-tiling",
         "Adaptive tiling and pinned per-bay workspaces",
         "The Web / Home", 5, 3, 3, "supported_api",
         "Existing KWin-backed desktop and native bay navigation",
         "https://system76.com/cosmic",
         ("kwin_supported_api", "wayland_screen_and_window_parity")),
    Idea("xdg-portal-permissions",
         "User-approved window sharing and screen awareness on Wayland",
         "System / Devices", 5, 3, 3, "supported_api",
         "Existing Spider Eye with visible consent and revocation",
         "https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html",
         ("explicit_screen_consent", "stop_revocation_verified")),
    Idea("plasma-68", "Plasma 6.8 target: make The Web Wayland-ready", "The Web / System",
         5, 5, 5, "release_upgrade", "Existing The Web, not a replacement session",
         "https://kde.org/announcements/plasma/6/6.8.0/",
         ("wayland_screen_and_window_parity", "supported_distribution_packages",
          "existing_services_preserved")),
    Idea("ubuntu-2610", "Ubuntu Studio 26.10 migration", "System / Recovery",
         4, 5, 5, "release_upgrade", "Existing installed Spider OS and active sda1 boot",
         "https://documentation.ubuntu.com/release-notes/26.10/",
         ("sda1_boot_sync_tested", "independent_backup_proven",
          "restore_rehearsal", "upgrader_offer_confirmed",
          "existing_services_preserved")),
)


# Best-app interim tool choices are part of the SAME native feature review.
# These candidates may be installed, absent, or already better than their
# alternatives on a particular host. No entry blindly displaces an app.
@dataclass(frozen=True)
class AppChoice:
    key: str
    bay: str
    task: str
    candidate: str
    detect_names: tuple[str, ...]
    strategy: str  # keep_if_present | trial_as_preferred
    spider_goal: str
    upstream: str
    special_checks: tuple[str, ...] = ()


APP_CHOICES = (
    AppChoice("file-manager", "Home / System", "File browsing, tabs and search",
              "Dolphin", ("dolphin",), "keep_if_present",
              "Native Spider file workspace", "https://apps.kde.org/dolphin/"),
    AppChoice("web-research", "Forage", "Browser with current project/session compatibility",
              "Firefox", ("firefox",), "keep_if_present",
              "Spider integrated browser and research tools", "https://www.mozilla.org/firefox/",
              ("current_web_sessions_preserved",)),
    AppChoice("office-docs", "Study / Productivity", "Office-compatible editing alongside LibreOffice",
              "ONLYOFFICE Desktop Editors", ("onlyoffice",), "trial_as_preferred",
              "Native Spider documents", "https://www.onlyoffice.com/desktop.aspx",
              ("docx_roundtrip", "libreoffice_retained_as_fallback")),
    AppChoice("longform-writing", "Author", "Novel chapter and manuscript assembly",
              "novelWriter", ("novelwriter",), "trial_as_preferred",
              "Spider Author manuscript editor", "https://novelwriter.io/",
              ("owner_original_manuscripts_unchanged", "docx_export_roundtrip")),
    AppChoice("research-citations", "Study / Deep Forage", "Local citation library and academic research",
              "Zotero", ("zotero",), "trial_as_preferred",
              "Spider citation and evidence library", "https://www.zotero.org/",
              ("zotero_api_local_only", "study_library_permission")),
    AppChoice("study-flashcards", "Study", "Spaced repetition and course review",
              "Anki", ("anki",), "trial_as_preferred",
              "Native Spider spaced repetition", "https://apps.ankiweb.net/",
              ("course_material_private",)),
    AppChoice("notes-sync", "Study / Productivity", "Local notes with optional OneDrive sync",
              "Joplin", ("joplin",), "trial_as_preferred",
              "Native Spider notes and sync", "https://joplinapp.org/",
              ("onedrive_preserve_current", "no_auto_sync_until_checked")),
    AppChoice("code-editor", "Dev Bay", "Lightweight coding and project editing",
              "Kate", ("kate",), "keep_if_present",
              "Native Spider source editor", "https://apps.kde.org/kate/"),
    AppChoice("code-ide", "Dev Bay", "Advanced extensions and code intelligence",
              "VSCodium", ("vscodium", "codium"), "trial_as_preferred",
              "Native Spider development workbench", "https://vscodium.com/",
              ("extensions_migration_review",)),
    AppChoice("art-paint", "Art Lab", "Digital painting, brushes and layered illustrations",
              "Krita", ("krita",), "keep_if_present",
              "Native Spider drawing and painting", "https://krita.org/",
              ("native_artwork_roundtrip",)),
    AppChoice("art-pictures", "Art Lab", "Photo retouching and bitmap manipulation",
              "GIMP", ("gimp",), "keep_if_present",
              "Native Spider image editor", "https://www.gimp.org/",
              ("existing_image_projects_unchanged",)),
    AppChoice("art-vector", "Art Lab", "Vectors, SVG and technical illustrations",
              "Inkscape", ("inkscape",), "keep_if_present",
              "Native Spider vector studio", "https://inkscape.org/"),
    AppChoice("art-3d", "Art Lab / Author", "3D assets and cinematic environments",
              "Blender", ("blender",), "keep_if_present",
              "Native Spider world editor", "https://www.blender.org/",
              ("cpu_gpu_budget_verified",)),
    AppChoice("art-raw", "Art Lab", "RAW photography workflow",
              "darktable", ("darktable",), "trial_as_preferred",
              "Native Spider photo development", "https://www.darktable.org/",
              ("photo_raw_non_destructive",)),
    AppChoice("video-editor", "Media / Art Lab", "Video editing and production timeline",
              "Kdenlive", ("kdenlive",), "keep_if_present",
              "Native Spider video editor", "https://kdenlive.org/",
              ("existing_video_projects_unchanged",)),
    AppChoice("video-player", "Media Center", "Modern local film playback",
              "Haruna", ("haruna",), "trial_as_preferred",
              "Spider Cinema player", "https://apps.kde.org/haruna/",
              ("video_decode_and_subtitles_verified",)),
    AppChoice("music-library", "Media Center", "Personal music library and high-quality playback",
              "Strawberry", ("strawberry",), "trial_as_preferred",
              "Spider Media music library", "https://www.strawberrymusicplayer.org/",
              ("bcn_broadcast_uninterrupted", "music_tags_preserved")),
    AppChoice("communications", "Communications / Productivity", "Email, calendar and contacts",
              "Kontact", ("kontact",), "trial_as_preferred",
              "Native Spider communications", "https://kontact.kde.org/",
              ("email_calendar_backup", "account_signin_explicit")),
    AppChoice("audio-daw", "Studio integration", "Professional multitrack recording",
              "Ardour", ("ardour",), "keep_if_present",
              "Existing Spider Audio Studio", "https://ardour.org/",
              ("audio_plugins_preserved", "bcn_broadcast_uninterrupted")),
    AppChoice("audio-routing", "Studio / Devices", "PipeWire audio and MIDI patchbay",
              "qpwgraph", ("qpwgraph",), "keep_if_present",
              "Native Spider audio routing", "https://github.com/rncbc/qpwgraph",
              ("audio_graph_preserved",)),
    AppChoice("devices-transfer", "Devices", "Pairing and file handoff between supported devices",
              "KDE Connect", ("kde connect", "kdeconnect"), "keep_if_present",
              "Native Spider devices integration", "https://apps.kde.org/kdeconnect/",
              ("user_approved_pairing",)),
    AppChoice("security-packets", "Kali Bay", "Authorized packet inspection",
              "Wireshark", ("wireshark",), "trial_as_preferred",
              "Native Spider packet analysis", "https://www.wireshark.org/",
              ("authorized_lab_only", "kali_isolation_preserved")),
    AppChoice("system-monitor", "System", "Real resource and process monitoring",
              "Plasma System Monitor", ("plasma system monitor", "plasma-systemmonitor"),
              "keep_if_present", "Native Spider system telemetry",
              "https://apps.kde.org/plasma-systemmonitor/"),
)

APP_TRANSITION_GATES = (
    "installed_application_inventory",
    "trusted_package_source",
    "real_task_test",
    "project_import_export_roundtrip",
    "native_bay_handoff",
    "acceptable_hardware_cost",
    "owner_selected_preferred_app",
    "former_app_available_for_rollback",
)


def app_choices(installed_apps=None) -> list[dict]:
    """Plan replacements using XDG menu items, never package removals.

    A visible menu hit is not evidence of functioning software; a menu miss
    is not proof the package is absent. None means not yet inventoried.
    """
    if installed_apps is None:
        inventory = None
    else:
        inventory = []
        for app in installed_apps:
            if isinstance(app, str):
                inventory.append(app.casefold())
            else:
                name = getattr(app, "name", "")
                desktop_id = getattr(app, "desktop_id", "")
                if not isinstance(name, str) or not isinstance(desktop_id, str):
                    raise TypeError("Installed application entry must be a name or XDG app")
                inventory.extend((name.casefold(), desktop_id.casefold()))
    output = []
    for choice in APP_CHOICES:
        if choice.strategy not in ("keep_if_present", "trial_as_preferred"):
            raise ValueError("Unsupported app selection strategy")
        if not choice.upstream.startswith("https://"):
            raise ValueError("Application needs authoritative source")
        matched = () if inventory is None else tuple(
            label for label in inventory
            if any(hint in label for hint in choice.detect_names))
        output.append({
            "key": choice.key, "bay": choice.bay, "task": choice.task,
            "candidate": choice.candidate, "spider_goal": choice.spider_goal,
            "strategy": choice.strategy, "source": choice.upstream,
            "visibility": "not_audited" if inventory is None else (
                "visible_in_app_menu" if matched else "not_seen_in_app_menu"),
            "required_checks": list(dict.fromkeys((
                *APP_TRANSITION_GATES, *choice.special_checks))),
            "preferred_app_changed": False,
            "old_application_removed": False,
            "spider_app_completed": False,
        })
    return output


def app_transition_text(installed_apps=None) -> str:
    """One in-bay review, no launcher, package action or default changes."""
    rows = app_choices(installed_apps)
    lines = [
        "BEST APPS / INTERIM TOOLS FOR EXISTING SPIDER OS BAYS",
        "Use proven software while original Spider applications mature.",
        "Menu visibility is not a functional test or a package audit.",
        "No current apps uninstalled, disabled, hidden or replaced.",
        "No app becomes preferred until tested, backed up and owner-approved.",
        "",
    ]
    for row in rows:
        kind = "KEEP IF WORKING" if row["strategy"] == "keep_if_present" else "TRIAL"
        lines.extend((
            "{} | {} | {}".format(row["bay"], row["candidate"], kind),
            "  Task: {} | Inventory: {}".format(row["task"], row["visibility"]),
            "  Spider destination: {}".format(row["spider_goal"]),
            "  Source: {}".format(row["source"]),
        ))
    lines.extend((
        "",
        "Stage: compare → test on host → owner selects default → retain fallback",
        "       → build Spider parity → verified switch → optional later removal.",
        "Uninstall and system-default changes are NEVER performed by this review.",
    ))
    return "\n".join(lines)


def validate(idea: Idea) -> None:
    if not isinstance(idea, Idea):
        raise TypeError("Expected a Spider OS feature idea")
    if not idea.key or not idea.title or not idea.bay or not idea.target:
        raise ValueError("Incomplete feature idea")
    if any(type(value) is not int or value not in range(1, 6)
           for value in (idea.benefit, idea.effort, idea.risk)):
        raise ValueError("Benefit, effort and risk must be integers from 1 to 5")
    if idea.mode not in MODES:
        raise ValueError("Unsupported adoption mode")
    if not idea.reuses_existing:
        raise ValueError("Duplicated bay, service or launcher is prohibited")
    if not idea.source.startswith("https://"):
        raise ValueError("A traceable upstream reference is required")
    if any(not gate or not isinstance(gate, str) for gate in idea.extra_gates):
        raise ValueError("Invalid verification gate")
    if len(set(idea.extra_gates)) != len(idea.extra_gates):
        raise ValueError("Repeated verification gate")


def score(idea: Idea) -> int:
    """Prefer improvements to real bays and penalize integration risk."""
    validate(idea)
    return 4 * idea.benefit - 2 * idea.effort - 2 * idea.risk + (
        2 if idea.mode == "source" else 0)


def evaluate(idea: Idea, passed_gates=()) -> dict:
    """A gate report, never an installer or authorization.

    Passing a gate means documented verification happened elsewhere; neither
    this function nor the UI can establish hardware compatibility on its own.
    """
    validate(idea)
    passed = frozenset(passed_gates)
    if any(not isinstance(gate, str) for gate in passed):
        raise ValueError("Gate names must be strings")
    all_gates = tuple(dict.fromkeys((*CORE_GATES, *idea.extra_gates)))
    unknown = passed.difference(all_gates)
    if unknown:
        raise ValueError("Unrecognized feature evidence: " + ", ".join(sorted(unknown)))
    outstanding = [gate for gate in all_gates if gate not in passed]
    return {
        "key": idea.key,
        "title": idea.title,
        "bay": idea.bay,
        "score": score(idea),
        "mode": idea.mode,
        "target": idea.target,
        "source": idea.source,
        "outstanding_gates": outstanding,
        "stage": "reviewed_for_release_preflight" if not outstanding
                 else "proposal_only",
        "installation_authorized": False,
    }


def prioritized(completed=None) -> list[dict]:
    """Rank current recommendations; never infer passed gates from host state."""
    completed = {} if completed is None else completed
    if not isinstance(completed, dict):
        raise TypeError("Completed evidence must be a per-feature mapping")
    known = {idea.key for idea in IDEAS}
    unknown = set(completed).difference(known)
    if unknown:
        raise ValueError("Unknown idea: " + ", ".join(sorted(unknown)))
    rows = [evaluate(idea, completed.get(idea.key, ())) for idea in IDEAS]
    return sorted(rows, key=lambda row: (-row["score"], row["key"]))


def summary_text(completed=None, limit=None) -> str:
    """Owner-readable Dev Bay report with explicit non-installable status."""
    if limit is None:
        limit = len(IDEAS)
    if type(limit) is not int or limit < 1 or limit > len(IDEAS):
        raise ValueError("Invalid report limit")
    lines = [
        "SPIDER OS / BEST IDEAS / EXISTING NATIVE BAYS",
        "Plasma 6.8 is a TARGET, not an installed or verified runtime.",
        "Borrow useful 26.10 and other-distro ideas without changing distro.",
        "Proposal and compatibility review only. NO changes or installs.",
        "Source-only compatibility is not proof of installed-host readiness.",
        "",
    ]
    for entry in prioritized(completed)[:limit]:
        lines.extend((
            "[{}] {} | {}".format(entry["score"], entry["bay"], entry["title"]),
            "  Integrate into: {}".format(entry["target"]),
            "  Route: {}".format(entry["mode"]),
            "  Remaining checks: {}".format(", ".join(entry["outstanding_gates"])
                                           or "none in proposal; release preflight still required"),
            "  Evidence: {}".format(entry["source"]),
            "",
        ))
    lines.append("Release remains under the existing protected Spider OS installer.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary_text())
