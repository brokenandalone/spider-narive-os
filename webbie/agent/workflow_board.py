"""Local-only JARVIS workflow board for Spider OS.

A workflow is a visible checklist with fixed workspace destinations, not a
model agent, task grant, shell script, scheduled job, or automation runner.
Only an explicit owner GUI click can open a selected workspace or mark a step.
Nothing is persisted and no private documents are read by this component.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

MAX_SECONDS = 900
MAX_STEPS = 6

# Only native The Web workspace keys, never program names, paths or URLs.
WORKSPACES = frozenset({
    "studio", "author", "study", "forage", "deep-forage", "webbie",
    "kali-bay", "media", "system", "recovery",
})


@dataclass(frozen=True)
class WorkflowStep:
    workspace: str
    title: str
    instruction: str


@dataclass(frozen=True)
class WorkflowBlueprint:
    key: str
    title: str
    steps: tuple[WorkflowStep, ...]


BLUEPRINTS = (
    WorkflowBlueprint("recording", "Prepare a recording session", (
        WorkflowStep("studio", "Inspect the active production board",
                     "Review the selected song and missing approved WAV stems."),
        WorkflowStep("studio", "Review the mix",
                     "Check track assignments and unfinished mix checkpoints."),
        WorkflowStep("forage", "Research only if needed",
                     "Find references in approved sources. Review citations."),
        WorkflowStep("studio", "Confirm recording readiness",
                     "Mark the next recording action yourself. No rendering."),
    )),
    WorkflowBlueprint("school", "Prepare coursework", (
        WorkflowStep("study", "Review course deadlines",
                     "Check the course schedule and current assignment."),
        WorkflowStep("deep-forage", "Gather vetted research",
                     "Open research tools and verify source references."),
        WorkflowStep("study", "Check APA and originality",
                     "Review citations and assignment rubric manually."),
        WorkflowStep("study", "Approve the final draft",
                     "Only you decide whether coursework is finished."),
    )),
    WorkflowBlueprint("canon", "Review Broken World continuity", (
        WorkflowStep("author", "Open the master canon",
                     "Inspect proposed versus established facts."),
        WorkflowStep("author", "Review relevant chapters",
                     "Confirm source anchors and character timelines."),
        WorkflowStep("forage", "Look up outside references if relevant",
                     "External material is never automatically canon."),
        WorkflowStep("author", "Decide canon changes",
                     "Accept or reject proposals inside Author."),
    )),
    WorkflowBlueprint("broadcast", "Prepare BCN broadcasting", (
        WorkflowStep("media", "Check the media center",
                     "Verify playback status and Nova health."),
        WorkflowStep("studio", "Review approved release audio",
                     "Confirm only reviewed masters are available."),
        WorkflowStep("media", "Prepare broadcaster controls",
                     "No live stream starts from this workflow board."),
    )),
    WorkflowBlueprint("maintenance", "Review Spider OS readiness", (
        WorkflowStep("system", "Inspect system health",
                     "Review diagnostics without changing services."),
        WorkflowStep("kali-bay", "Inspect authorized security workspace",
                     "Open only the authorized lab and existing reports."),
        WorkflowStep("recovery", "Review the backup plan",
                     "No backups are modified by this board."),
    )),
)


def blueprint_for(key: str) -> WorkflowBlueprint:
    """Resolve only exact built-in identifiers. Never interpret model output."""
    if not isinstance(key, str):
        raise ValueError("Choose a fixed workflow")
    for plan in BLUEPRINTS:
        if key == plan.key:
            if not 1 <= len(plan.steps) <= MAX_STEPS:
                raise ValueError("Unreviewed workflow size")
            for item in plan.steps:
                if item.workspace not in WORKSPACES:
                    raise ValueError("Workflow references an unknown workspace")
            return plan
    raise ValueError("Unsupported workflow")


class WorkflowSession:
    """Ephemeral owner-click checklist with a maximum 15-minute lifetime."""

    def __init__(self, *, clock=None):
        self.clock = clock or time.monotonic
        self.cancel()

    def cancel(self):
        self.plan = None
        self.position = 0
        self.expires_at = 0.0
        self.stopped = True

    def begin(self, key, *, owner_approved=False, seconds=600):
        if owner_approved is not True:
            raise PermissionError("Owner must confirm a workflow in the GUI")
        if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
            raise ValueError("Workflow duration must be bounded")
        plan = blueprint_for(key)
        # Replace previous plans rather than permitting overlapping tasks.
        self.cancel()
        self.plan = plan
        self.position = 0
        self.expires_at = self.clock() + seconds
        self.stopped = False
        return self.current()

    def current(self):
        if self.stopped or self.plan is None:
            return None
        if self.clock() >= self.expires_at:
            self.cancel()
            return None
        if self.position >= len(self.plan.steps):
            self.cancel()
            return None
        return self.plan.steps[self.position]

    def complete(self, *, owner_confirmed=False, expected_position=None):
        """The board cannot infer completion from a model or window observation."""
        if owner_confirmed is not True:
            raise PermissionError("Only a deliberate GUI completion click is allowed")
        item = self.current()
        if item is None:
            return None
        if type(expected_position) is not int or expected_position != self.position:
            raise ValueError("Stale or out-of-order workflow confirmation")
        self.position += 1
        next_item = self.current()
        return next_item

    def status(self):
        item = self.current()
        if item is None:
            return {"active": False, "step": 0, "total": 0, "workspace": None}
        return {
            "active": True, "step": self.position + 1,
            "total": len(self.plan.steps), "workspace": item.workspace,
        }
