"""Webbie multi-turn conversation timing and explicit end semantics.

STOP interrupts the current response, but does not END the conversation.
"That's all" ends the follow-up window while the wake listener stays active.
The installed PC already has a customized voice loop; this source helper must
be reconciled into that owner-tested loop, not replace it.
"""
import re

FOLLOWUP_SECONDS = 45
END_PHRASES = frozenset({
    "that's all", 'thats all', "that's all folks", 'thats all folks',
    'end conversation', 'end our conversation',
})


def normalize(text):
    return re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9' ]", ' ', str(text).casefold())).strip()


def is_end_conversation(text):
    phrase = normalize(text)
    for prefix in ('hey webbie ', 'hey webby ', 'webbie ', 'webby ', 'web '):
        if phrase.startswith(prefix):
            phrase = phrase[len(prefix):]
            break
    return phrase in END_PHRASES


def next_window(current_until, event, now, seconds=FOLLOWUP_SECONDS):
    if event in ('sleep', 'end'):
        return 0.0
    if event in ('wake', 'command', 'stop'):
        # Explicit stop leaves the session available for a corrected command.
        return max(float(current_until), float(now) + float(seconds))
    raise ValueError('Unsupported conversation event')
