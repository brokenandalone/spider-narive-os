"""Private in-process resilience governor for Webbie's local Ollama chat.

Does NOT swap/download models, contact a cloud endpoint, retry a prompt,
run desktop commands, store user messages, or restart a service. It only
bounds repeated local failures and reports coarse health metadata.
"""
from __future__ import annotations
import os
import threading
import time

MAX_FAILURES = 3
OPEN_SECONDS = 45


def response_timeout(env=None):
    """Local CPU-friendly default; owner can configure 10..180 seconds."""
    env=os.environ if env is None else env
    try:
        value=int(env.get("WEBBIE_OLLAMA_TIMEOUT_SECONDS","90"))
    except (TypeError,ValueError,OverflowError):
        return 90
    return value if 10<=value<=180 else 90


class ModelResilience:
    def __init__(self, *, clock=None, failure_limit=MAX_FAILURES,
                 cooldown=OPEN_SECONDS):
        if (type(failure_limit) is not int or not 1<=failure_limit<=10
                or not 1<=cooldown<=600):
            raise ValueError("Unsafe model resilience settings")
        self.clock=clock or time.monotonic
        self.failure_limit=failure_limit
        self.cooldown=cooldown
        self.lock=threading.RLock()
        self.failure_count=0
        self.open_until=0.0
        self.trial_running=False
        self.last_outcome="unknown"

    def acquire(self):
        """True means one LOCAL Ollama request is permitted.

        Once the breaker reopens, exactly one half-open trial can run at
        a time; repeated requests fail fast rather than piling up.
        """
        with self.lock:
            now=float(self.clock())
            if self.open_until:
                if now<self.open_until or self.trial_running:
                    return False
                self.trial_running=True
            return True

    def finish(self, *, succeeded):
        if type(succeeded) is not bool:
            raise ValueError("Model outcome must be true or false")
        with self.lock:
            self.trial_running=False
            if succeeded:
                self.failure_count=0
                self.open_until=0.0
                self.last_outcome="responded"
            else:
                self.failure_count+=1
                self.last_outcome="unavailable"
                if self.failure_count>=self.failure_limit:
                    self.open_until=float(self.clock())+self.cooldown

    def status(self):
        with self.lock:
            now=float(self.clock())
            blocked=self.open_until>now or self.trial_running
            return {
                "status":("temporarily_paused" if blocked else
                          "ready_to_try" if self.failure_count else "normal"),
                "consecutive_failures":min(self.failure_count,self.failure_limit),
                "retry_after_seconds":(
                    max(0,int(self.open_until-now+0.999)) if blocked else 0),
                "last_outcome":self.last_outcome,
            }


MODEL_GOVERNOR = ModelResilience()


def model_health_message(state=None):
    state=MODEL_GOVERNOR.status() if state is None else state
    if state["status"]=="temporarily_paused":
        return ("Webbie's local AI model had repeated failures. "
                "New AI requests are briefly paused, not restarted. "
                f"Try again in about {state['retry_after_seconds']} seconds.")
    if state["status"]=="ready_to_try":
        return "Local AI has had a recent failure and is ready for another attempt."
    return ("Local AI request protection is active. This is not a "
            "live hardware or model-quality test.")
