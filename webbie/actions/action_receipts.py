"""Trustworthy, content-free receipts for Webbie desktop operations.

A desktop command returning without error is only REQUESTED, not proof of
browser load, file change, screenshot interpretation, or task completion.
Receipts store no URL, coordinates, text, filenames, or window titles.
"""
from __future__ import annotations
from dataclasses import dataclass
import time

ACTIONS=frozenset({"website","application","window","navigation","observation","stop"})
OUTCOMES=frozenset({"requested","denied","failed","observed","canceled"})
MAX_AGE=90

@dataclass(frozen=True)
class ActionReceipt:
    action: str
    outcome: str
    issued_at: float

def status_text(receipt):
    if not isinstance(receipt,ActionReceipt):
        return "No recent desktop action receipt."
    phrases={
        "requested":"request sent; completion not verified",
        "denied":"not approved or denied",
        "failed":"request failed",
        "observed":"local authorized observation occurred",
        "canceled":"operation canceled",
    }
    return f"{receipt.action.title()}: {phrases[receipt.outcome]}."

class ActionReceipts:
    def __init__(self, *, clock=None):
        self.clock=clock or time.monotonic
        self.latest=None

    def record(self, action, outcome):
        if not isinstance(action,str) or action not in ACTIONS:
            raise ValueError("Unknown redacted action class")
        if not isinstance(outcome,str) or outcome not in OUTCOMES:
            raise ValueError("Unknown action result")
        self.latest=ActionReceipt(action,outcome,float(self.clock()))
        return self.latest

    def snapshot(self):
        item=self.latest
        if item is None or not 0<=self.clock()-item.issued_at<=MAX_AGE:
            self.latest=None
            return None
        return item

    def clear(self):
        self.latest=None

    def summary(self):
        return status_text(self.snapshot())

    def advisory_summary(self):
        item=self.snapshot()
        if item is None:
            return ""
        # A single controlled sentence, never raw browser/site/model data.
        return status_text(item)
