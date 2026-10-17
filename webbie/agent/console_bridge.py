"""Literal owner-directed local console diagnostics, never generated shell code.

This bridge gives Webbie verified, auditable LOCAL system observations that
can be shown in her chat or spoken aloud. It is not a PTY, shell interpreter,
sudo, an arbitrary OS runner, or permission to execute terminal output.
"""
from __future__ import annotations
import re
import subprocess

COMMANDS={
    "check kernel":("uname","-r"),
    "show kernel":("uname","-r"),
    "check uptime":("uptime","-p"),
    "show uptime":("uptime","-p"),
    "check memory":("free","-h"),
    "show memory":("free","-h"),
    "check disk space":("df","-h","--","/"),
    "show disk space":("df","-h","--","/"),
    "check webbie service":("systemctl","--user","is-active","webbie.service"),
    "check nova service":("systemctl","--user","is-active","spider-ai-dj.service"),
    "check ollama service":("systemctl","--user","is-active","ollama.service"),
}
CMD_PREFIX=re.compile(
    r"^(?:(?:hey\s+)?(?:webbie|webby)\s*[,.:]?\s+)?"
    r"(?:console\s+|konsole\s+|in\s+console\s+|in\s+konsole\s+)?"
    r"(?P<command>check kernel|show kernel|check uptime|show uptime|"
    r"check memory|show memory|check disk space|show disk space|"
    r"check webbie service|check nova service|check ollama service)"
    r"[.!?]?$",re.I,
)
OPEN=re.compile(
    r"^(?:(?:hey\s+)?(?:webbie|webby)\s*[,.:]?\s+)?"
    r"(?:open|launch|start)\s+(?:the\s+)?(?:konsole|console)\s*[.!?]?$",
    re.I,
)


def parse_console_request(text):
    if not isinstance(text,str) or not 1<=len(text)<=130 or "\n" in text:
        return None
    if OPEN.fullmatch(text.strip()):
        return ("open",None)
    match=CMD_PREFIX.fullmatch(text.strip())
    if match:
        key=" ".join(match.group("command").lower().split())
        return ("diagnostic",key)
    return None


def perform_console_request(text, *, authorized, runner=subprocess.run,
                            launcher=subprocess.Popen):
    """Caller must check saved unpaused owner permission and literal source."""
    parsed=parse_console_request(text)
    if parsed is None:
        return None
    if authorized is not True:
        return "Webbie's permanent console permission is paused or not authorized."
    kind,key=parsed
    if kind=="open":
        try:
            launcher(["konsole"],stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                     close_fds=True,start_new_session=True)
            return "Konsole launch requested. Window readiness is not verified."
        except OSError:
            return "Konsole could not be launched. No terminal command was run."
    args=COMMANDS[key]
    try:
        result=runner(
            list(args),capture_output=True,text=True,
            timeout=8,check=False)
        raw=result.stdout if result.returncode==0 else "Command unavailable"
        output="".join(ch for ch in raw if ch in "\n\t" or ch.isprintable())
        output=output.strip()[:1200]
        if not output:
            output="No diagnostic result reported."
        return f"Console diagnostic ({key}):\n{output}"
    except (OSError,subprocess.TimeoutExpired,ValueError,UnicodeError):
        return "Console diagnostic could not finish; nothing was changed."
