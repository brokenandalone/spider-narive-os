"""Webbie Unified Workflow: bounded Brain/Eyes/Hands/Autopilot coordination.

A GUI-owned IN-MEMORY checklist for one owner-curated focus task.
No instructions from models, websites, screenshots, or microphones can create
a grant, stage actions, or confirm success. Owner clicks remain necessary.
This is supervised task tracking, NOT autonomous desktop execution.
"""
from __future__ import annotations
import re
import threading
import time

ALLOWED_WORKSPACES=frozenset({
    "default","studio","author","study","kali-bay","forage",
    "deep-forage","media","art-lab","dev-bay","system",
    "recovery","communications","games","webbie",
})
PHASES=frozenset(("idle","observe","review_action","verify","done","canceled"))
ACTION_TYPES=frozenset(("application","website","navigation","window"))
ACTION_OUTCOMES=frozenset(("requested","denied","failed","observed","canceled"))
MAX_DURATION=1800
MAX_REVIEWED_STEPS=4


class UnifiedWorkflow:
    """One context-bounded mission; all transitions require owner GUI input."""

    def __init__(self, *, clock=None):
        self.clock=clock or time.monotonic
        self.lock=threading.RLock()
        self.generation=0
        self._reset("idle")

    def _reset(self,phase):
        self.phase=phase
        self.workspace=""
        self.task_id=""
        self.task_title=""
        self.expires=0.0
        self.observation=False
        self.action=""
        self.outcome=""
        self.completed=False
        self.step_number=0
        self.confirmed_steps=0

    def _ensure_current(self, workspace=None):
        if self.phase in ("idle","canceled","done"):
            return
        if (self.clock()>=self.expires or
            (workspace is not None and workspace!=self.workspace)):
            self.generation+=1
            self._reset("canceled")

    def begin(self, task, *, workspace):
        """Owner-click only: take an existing task, never LLM text."""
        if (not isinstance(task,dict) or workspace not in ALLOWED_WORKSPACES or
            task.get("workspace")!=workspace or task.get("status")!="active" or
            not isinstance(task.get("id"),str) or
            re.fullmatch(r"[0-9a-f]{32}",task["id"]) is None or
            not isinstance(task.get("title"),str) or
            not 1<=len(task["title"])<=100):
            raise ValueError("Choose an existing active focus task")
        with self.lock:
            self.generation+=1
            self._reset("observe")
            self.workspace=workspace
            self.task_id=task["id"]
            self.task_title=task["title"]
            self.expires=self.clock()+MAX_DURATION
            self.step_number=1
            return self.generation

    def observed_window(self, *, from_consented_gui=False, workspace=None):
        """Triggered by completed, consented screen inspection only."""
        with self.lock:
            self._ensure_current(workspace)
            if self.phase!="observe" or from_consented_gui is not True:
                return False
            self.observation=True
            self.phase="review_action"
            return True

    def record_action(self, action, outcome, *, from_control_gui=False,
                      workspace=None):
        """Track real GUI receipts, NEVER infer that request means success."""
        with self.lock:
            self._ensure_current(workspace)
            if (from_control_gui is not True or self.phase!="review_action"
                    or action not in ACTION_TYPES or
                    outcome not in ACTION_OUTCOMES):
                return False
            self.action=action
            self.outcome=outcome
            if outcome=="requested":
                self.phase="verify"
            elif outcome=="canceled":
                self.generation+=1
                self._reset("canceled")
            # A denied/failed/observed action cannot prove a change happened.
            return True

    def confirm_result(self, *, owner_confirmed=False, workspace=None):
        """Use only after an explicit owner GUI confirmation and visual check."""
        with self.lock:
            self._ensure_current(workspace)
            if self.phase!="verify" or owner_confirmed is not True:
                return False
            self.phase="done"
            self.completed=True
            self.confirmed_steps+=1
            return True

    def next_reviewed_step(self, *, owner_clicked=False, workspace=None):
        """An owner manually starts another full observe/action/verify cycle."""
        with self.lock:
            self._ensure_current(workspace)
            if (self.phase!="done" or owner_clicked is not True
                    or self.confirmed_steps>=MAX_REVIEWED_STEPS):
                return False
            self.generation+=1
            self.step_number=self.confirmed_steps+1
            self.phase="observe"
            self.observation=False
            self.action=""
            self.outcome=""
            self.completed=False
            return True

    def retry(self, *, owner_clicked=False, workspace=None):
        with self.lock:
            self._ensure_current(workspace)
            if self.phase!="verify" or owner_clicked is not True:
                return False
            self.phase="observe"
            self.observation=False
            self.action=""
            self.outcome=""
            return True

    def stop(self):
        with self.lock:
            self.generation+=1
            self._reset("canceled")

    def snapshot(self, *, workspace=None):
        with self.lock:
            self._ensure_current(workspace)
            phase=self.phase
            return {
                "phase":phase,
                "workspace":self.workspace,
                "task_title":self.task_title,
                "observation_reported":self.observation,
                "last_action":self.action,
                "last_outcome":self.outcome,
                "completed":self.completed,
                "step_number":self.step_number,
                "confirmed_steps":self.confirmed_steps,
                "max_steps":MAX_REVIEWED_STEPS,
                "next_step":{
                    "idle":"Select an active Focus Task and click Start.",
                    "observe":"Use Computer Control to authorize one window and click Inspect window once.",
                    "review_action":"Review an operation in Computer Control. Every operation still needs its own authorization.",
                    "verify":"Request sent. Examine the result yourself and confirm, or try again.",
                    "done":"Owner verified this step. Start another reviewed step if needed. No actions are authorized.",
                    "canceled":"Stopped, expired or changed workspace. Start a new workflow.",
                }[phase],
            }

    def advisory_status(self, *, workspace=None):
        state=self.snapshot(workspace=workspace)
        # Only allowlisted phase, no task text, screen content or secrets.
        return ("Unified workflow: "+state["phase"]+
                ". This is advisory and never authorizes computer control.")
