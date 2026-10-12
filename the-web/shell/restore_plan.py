"""Time-sliced, user-controllable Spider OS tab-restoration plan.

This pure-data module makes no network, process, file or Qt calls.
The desktop GUI drives a bounded, validated plan one workspace per Qt turn.
"""
from desktop_state import clean_state


class RestorePlan:
    def __init__(self, raw, allowed):
        safe = clean_state(raw, allowed)
        self.order = list(safe['open'])
        self.pending = [key for key in self.order if key != 'default']
        self.active = safe['active']
        self.cancelled = False
        self.paused = False
        self.attempted = []
        self.skipped = []

    def pop(self):
        if self.cancelled or self.paused or not self.pending:
            return None
        name = self.pending.pop(0)
        self.attempted.append(name)
        return name

    def acknowledge(self, name):
        """Prevent a manually opened tab from being reopened by the queue."""
        if name not in self.pending:
            return False
        self.pending.remove(name)
        self.attempted.append(name)
        return True

    def prioritize(self, name):
        if self.cancelled or name not in self.pending:
            return False
        self.pending.remove(name)
        self.pending.insert(0, name)
        return True

    def skip(self, name):
        """Skip this launch only; the saved session file is left untouched."""
        if self.cancelled or name not in self.pending:
            return False
        self.pending.remove(name)
        self.skipped.append(name)
        return True

    def pause(self):
        if self.cancelled or not self.pending:
            return False
        self.paused = True
        return True

    def resume(self):
        if self.cancelled or not self.paused:
            return False
        self.paused = False
        return True

    def done(self):
        return self.cancelled or not self.pending

    def cancel(self):
        self.cancelled = True
        self.paused = False
        self.pending.clear()

    def progress(self):
        total = max(0, len(self.order) - 1)
        return len(self.attempted) + len(self.skipped), total

    def report(self):
        complete, total = self.progress()
        return {
            'processed': complete,
            'total': total,
            'remaining': len(self.pending),
            'paused': self.paused,
            'cancelled': self.cancelled,
            'skipped': tuple(self.skipped),
            'next': self.pending[0] if self.pending else None,
        }


def desired_tab_order(plan, visible):
    """Respect saved tab order, retaining additional user-opened tabs."""
    visible = list(visible)
    ordering = [name for name in plan.order if name in visible]
    ordering += [name for name in visible if name not in ordering]
    if 'default' in ordering:
        ordering.remove('default')
    return ['default'] + ordering
