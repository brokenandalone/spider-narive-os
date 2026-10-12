"""Safe, predictable workspace tab navigation for The Web.

Pure data helpers keep keyboard cycling and session order testable without Qt.
They never execute commands, access user documents, or manipulate applications.
"""


def canonical_tabs(names, allowed):
    """Keep The Web home at position zero and remove unknown/duplicate tabs."""
    valid = set(allowed)
    ordered = ['default']
    for name in names:
        if name != 'default' and isinstance(name, str) and name in valid and name not in ordered:
            ordered.append(name)
    return ordered


def adjacent_index(count, current, direction):
    """Wrap forward/back through all visible tabs, including home."""
    if not isinstance(count, int) or count <= 0:
        return -1
    if not isinstance(current, int) or current < 0 or current >= count:
        return 0
    return (current + (1 if direction >= 0 else -1)) % count


def other_tab_names(names, selected, allowed):
    """Close candidates, excluding home and the selected workspace."""
    if selected == 'default':
        return [name for name in canonical_tabs(names, allowed)
                if name != 'default']
    return [name for name in canonical_tabs(names, allowed)
            if name not in ('default', selected)]


def workspace_context_summary(current, opened, detail='', maximum=600):
    """Share navigation labels with Webbie only when an owner sends a request.

    Do not include window titles, desktop paths, document contents, active
    URLs, clipboard text, or other automatically observed information.
    """
    names = [str(label)[:60] for label in opened if isinstance(label, str)][:30]
    parts = ['Current workspace: ' + str(current)[:60],
             'Open workspace tabs: ' + ', '.join(names[:12])]
    if detail:
        parts.append('Workspace-provided description: ' + str(detail)[:250])
    return '; '.join(parts)[:max(0, min(int(maximum), 600))]
