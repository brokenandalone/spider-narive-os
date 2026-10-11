"""Time-sliced desktop-session restoration planning.

A plan contains only known workspace identifiers. It performs no I/O or
workspace instantiation. The GUI drives the plan one workspace per Qt tick.
"""
from desktop_state import clean_state


class RestorePlan:
    def __init__(self, raw, allowed):
        safe = clean_state(raw, allowed)
        self.order = list(safe['open'])
        self.pending = [name for name in self.order if name != 'default']
        self.active = safe['active']
        self.cancelled = False

    def pop(self):
        if self.cancelled or not self.pending:
            return None
        return self.pending.pop(0)

    def done(self):
        return self.cancelled or not self.pending

    def cancel(self):
        self.cancelled = True
        self.pending.clear()

    def progress(self):
        total = max(0, len(self.order) - 1)
        return total - len(self.pending), total


def desired_tab_order(plan, visible):
    """Restore original order when tabs were added while startup ran."""
    visible = list(visible)
    ordering = [name for name in plan.order if name in visible]
    ordering += [name for name in visible if name not in ordering]
    if 'default' in ordering:
        ordering.remove('default')
    return ['default'] + ordering
