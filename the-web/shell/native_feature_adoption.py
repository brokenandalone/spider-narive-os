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
    Idea("plasma-68", "Plasma 6.8 desktop compatibility", "The Web / System",
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
