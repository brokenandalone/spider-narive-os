"""Bounded, read-only workspace source checks for The Web recovery panel.

No directory scanning, source execution, subprocess, webcam, network or
reading of manuscripts is performed by this module.
"""
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class WorkspaceHealth:
    ident: str
    label: str
    status: str
    detail: str

def check_workspaces(root, names, native_modules, loaded=(), failures=None):
    base = Path(root).resolve(strict=False)
    loaded = set(loaded)
    failures = failures or {}
    rows = []
    for ident, label in names.items():
        if ident == 'default':
            continue
        if ident in failures:
            status, detail = 'needs-attention', 'Workspace did not load. Retry from The Web.'
        elif ident not in native_modules:
            status, detail = ('open' if ident in loaded else 'available'), 'Managed by The Web or installed apps'
        else:
            folder, filename, _ = native_modules[ident]
            file_path = (base / folder / filename).resolve(strict=False)
            try:
                confined = file_path.is_relative_to(base)
                present = confined and file_path.is_file()
            except OSError:
                present = False
            if not present:
                status, detail = 'missing', 'Workspace module was not found in the Spider OS installation'
            elif ident in loaded:
                status, detail = 'open', 'Native workspace loaded'
            else:
                status, detail = 'available', 'Native workspace source detected'
        rows.append(WorkspaceHealth(ident, str(label)[:70], status, detail))
    return rows
