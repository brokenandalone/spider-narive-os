"""Bounded WirePlumber controls for the current default output."""
import re
import shutil
import subprocess


def audio_command(arguments):
    tool = shutil.which('wpctl')
    if not tool: raise RuntimeError('WirePlumber audio controls are unavailable. Open KDE Audio settings.')
    try:
        result = subprocess.run([tool, *arguments], capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('The audio service did not respond') from None
    if result.returncode: raise RuntimeError('The audio command failed. Check the default output and audio services.')
    return result.stdout[:4096]


def adjust_audio(action):
    if action == 'Up': args = ['set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '5%+']
    elif action == 'Down': args = ['set-volume', '@DEFAULT_AUDIO_SINK@', '5%-']
    elif action == 'Mute': args = ['set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle']
    else: raise ValueError('Unsupported audio control')
    audio_command(args)


def output_level():
    try: text = audio_command(['get-volume', '@DEFAULT_AUDIO_SINK@'])
    except RuntimeError as error: return str(error)
    match = re.search(r'Volume:\s*([0-9]+(?:\.[0-9]+)?)', text)
    if not match: return 'Output volume unavailable'
    return f'Output: {round(float(match.group(1)) * 100)}%' + (' · Muted' if '[MUTED]' in text else '')
