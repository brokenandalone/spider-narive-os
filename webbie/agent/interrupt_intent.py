"""High-priority Webbie stop intent, shared by future audio and desktop adapters.

Speech-to-text can render Webbie as 'Webby'. Recognize only an entire,
deliberately addressed command; never match an embedded instruction in a
document, a webpage, or a sentence. This matcher does not itself stop audio:
the installed voice service needs a concurrently active interruption listener
and direct TTS cancellation, neither supplied by string matching alone.
"""
import re

STOP = frozenset({
    'stop', 'stop now', 'stop please', 'stop talking', 'stop speaking',
    'stop talking now', 'stop speaking now', 'be quiet', 'quiet', 'shut up',
    'cancel', 'cancel that', 'stop that',
})
WAKE = frozenset({'webbie', 'webby', 'web'})


def normalize(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', str(text).casefold())).strip()


def is_direct_stop(text):
    words = normalize(text).split()
    if words and words[0] == 'hey':
        words.pop(0)
    if not words or words[0] not in WAKE:
        return False
    words.pop(0)
    return ' '.join(words) in STOP
