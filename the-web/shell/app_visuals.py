"""Spider OS native app identity assets, source-controlled and app-specific.

Only existing real workspaces get clickable icons. Artwork for not-yet-built
commercial apps is kept as design assets, never exposed as working software.
"""
from pathlib import Path

APP_SYMBOLS = {
    "studio": "spider-audio-studio",
    "art-lab": "spider-art-lab",
    "author": "spider-author",
    "study": "spider-study",
    "media": "spider-media-center",
    "communications": "spider-connect",
    "kali-bay": "spider-security",
    "system": "spider-control",
    "webbie": "spider-webbie",
    "forage": "spider-forage",
    "deep-forage": "spider-deep-forage",
    "dev-bay": "spider-dev",
    "recovery": "spider-recovery",
}

def app_art(root, workspace, kind="icons"):
    """Return a real asset path if installed; caller provides existing fallback."""
    if kind not in ("icons", "backgrounds"):
        raise ValueError("Unsupported app artwork kind")
    slug = APP_SYMBOLS.get(workspace)
    if not slug:
        return None
    path = Path(root) / "branding" / "spider-apps" / kind / (slug + ".svg")
    return path if path.is_file() else None
