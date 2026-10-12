"""Small content-free counters for troubleshooting Webbie microphone intake.

No speech text, audio, speaker names, window titles, addresses, credentials,
recordings or voiceprints. Counts are process-local and reset on restart.
They are NOT measurements of speaker biometric accuracy.
"""
from __future__ import annotations
import threading

EVENTS=(
    "heard_transcript", "rejected_unverified", "verified_input",
    "emergency_stop", "queued_command", "ignored_sleeping",
)


class VoiceIntakeMeter:
    def __init__(self):
        self.lock=threading.RLock()
        self.values={name:0 for name in EVENTS}

    def count(self, event):
        if event not in EVENTS or not isinstance(event,str):
            raise ValueError("Unknown anonymized voice counter")
        with self.lock:
            self.values[event]=min(1_000_000,self.values[event]+1)

    def snapshot(self):
        with self.lock:
            return dict(self.values)

    def clear(self):
        with self.lock:
            self.values={name:0 for name in EVENTS}


VOICE_INTAKE = VoiceIntakeMeter()


def display_meter(data):
    if not isinstance(data,dict):
        return "No readable voice activity counters from the resident service."
    values={}
    for name in EVENTS:
        value=data.get(name)
        if type(value) is not int or not 0<=value<=1_000_000:
            return "No valid voice activity counters from the resident service."
        values[name]=value
    return ("Since the last Webbie service start (counts, no conversations saved):\n"
            f"Audio chunks yielding text: {values['heard_transcript']}\n"
            f"Commands ignored without speaker proof: {values['rejected_unverified']}\n"
            f"Verified speech inputs: {values['verified_input']}\n"
            f"Emergency STOP requests: {values['emergency_stop']}\n"
            f"Queued voice corrections: {values['queued_command']}\n"
            f"Ignored while sleeping: {values['ignored_sleeping']}\n"
            "These counts are not calibrated voice recognition accuracy.")
