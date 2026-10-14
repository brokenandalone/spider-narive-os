"""Wave 8 Studio production readiness. Explicit folder; no rendering or writes."""
from __future__ import annotations
from collections import Counter
import re

from operations_batch import studio_session_report
from operations_wave8_core import selected_folder

ROLES = {
    "vocal": r"(?:^|[_ .-])(?:lead[_ -]?vocals?|vocals?|voice|singer)(?:[_ .-]|$)",
    "guitar": r"(?:^|[_ .-])(?:guitars?|rhythm|lead[_ -]?guitar)(?:[_ .-]|$)",
    "bass": r"(?:^|[_ .-])bass(?:[_ .-]|$)",
    "drums": r"(?:^|[_ .-])(?:drums?|kick|snare|cymbals?|percussion)(?:[_ .-]|$)",
    "keys": r"(?:^|[_ .-])(?:piano|keys?|synth|organ)(?:[_ .-]|$)",
    "ambient": r"(?:^|[_ .-])(?:pad|ambient|atmosphere|fx|sfx)(?:[_ .-]|$)",
}


def production_brief(folder):
    """Report formats and *possible* named stems, not mixing or track assignment."""
    result = dict(studio_session_report(folder))
    tracks = selected_folder(folder, {".wav"}, 24)
    counts = Counter()
    unnamed = 0
    multi_role = 0
    for file in tracks:
        name = file.stem.casefold()
        roles = [role for role, pattern in ROLES.items()
                 if re.search(pattern, name, re.I)]
        if not roles:
            unnamed += 1
        if len(roles) > 1:
            multi_role += 1
        counts.update(roles)
    problems = []
    if result["format_mismatch"]:
        problems.append("WAV rates or sample formats differ; review before mixing.")
    if result["unreadable_track_indices"]:
        problems.append("Some WAV stems were unreadable; inspect originals.")
    if result["duration_spread_seconds"] and result["duration_spread_seconds"] > 1:
        problems.append("Stem lengths differ; align by timeline, not file duration alone.")
    if result["near_full_scale_samples_in_sampled_edges"]:
        problems.append("Sampled edges contain values near full scale; inspect peaks.")
    return {
        "workspace": "Studio",
        "mode": "read_only",
        "operation": "production_brief",
        "stem_inventory": result,
        "suggested_filename_role_counts": dict(sorted(counts.items())),
        "stems_without_obvious_role": unnamed,
        "stems_matching_multiple_roles": multi_role,
        "review_flags": problems,
        "note": "Filename roles are guesses. No song metadata, vocal identity, "
                "real LUFS, mastering, generation or actual DAW session is verified.",
    }
