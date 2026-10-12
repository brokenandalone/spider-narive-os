"""Single-click owner approval for routine Webbie app access.

This is an ephemeral owner-GUI policy, NOT full device or cloud permission.
Permits discovering/launching selected ordinary installed XDG apps,
inspecting/focusing a manually selected window, and benign navigation keys.
Cannot authorize keyboard text, clicks, delete, saving, spending, messaging,
shell/root, installs, Kali offensive activity, system config or browser
external navigation. Risky operations are always DENIED in wide mode.
Connected services require their own pre-existing app authentication and
a separately audited, read-only adapter. None is silently installed.
"""
from __future__ import annotations
import re
import threading
import time

SESSION_SECONDS=1800
MAX_ACTIONS=240
MAX_APPS=2000
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]{0,199}\.desktop$")
# Conservative denylist for privileged/security/system-editing/remote execution.
# Matches whole tokens; broad access will never open an unknown risky category.
BLOCK_TOKENS=frozenset((
    "terminal","konsole","xterm","qterminal","tilix","alacritty",
    "sudo","root","admin","pkexec","polkit","policykit","systemsettings",
    "settings","partition","gparted","gnome-disks","disk-utility",
    "firewall","ufw","wireshark","metasploit","burpsuite","hydra",
    "nmap","sqlmap","john","hashcat","aircrack","kali",
    "password","keepass","keyring","seahorse","wallet",
    "virtualbox","qemu","virt-manager","remote","ssh","vnc","rdp",
    "appimage-installer","software-center","discover","packagekit",
))
BENIGN_KEYS=frozenset((
    "Escape","Tab","Up","Down","Left","Right","Home","End",
    "Page_Up","Page_Down","space","alt+Left","alt+Right",
    "ctrl+Page_Up","ctrl+Page_Down",
))
ROUTINE_ACTIONS=frozenset((
    "observe.apps","observe.windows","app.open",
    "window.focus","window.target","keyboard.key","task.begin",
))
# No service permission is granted by this module. Service adapters
# will need action-by-action audited read-only contracts elsewhere.
BLOCKED_ACTIONS=frozenset((
    "pointer.click","keyboard.type","keyboard.change.confirm",
    "window.close.confirm","browser.open.confirm",
    "service.write","service.delete","service.send","service.purchase",
    "system.install","system.restart","system.security",
    "git.push","radio.broadcast","kali.execute",
))


def safe_app_id(value):
    if not isinstance(value,str) or ID.fullmatch(value) is None:
        return False
    tokens=set(re.findall(r"[a-z0-9]+",value.casefold()))
    # Exact segments and multiword substrings are both checked to reject
    # privileged menus while allowing ordinary installed application IDs.
    lower=value.casefold().removesuffix(".desktop")
    for blocked in BLOCK_TOKENS:
        if blocked in tokens or blocked in lower:
            return False
    return True


class OwnerSafeAccess:
    """In-process opt-in, fail-closed, zero-persistence policy gate."""

    def __init__(self,*,clock=None):
        self.clock=clock or time.monotonic
        self._lock=threading.RLock()
        self._enabled=False
        self._expires=0.0
        self._left=0
        self._apps=frozenset()

    def activate(self,app_ids,*,owner_clicked=False,seconds=SESSION_SECONDS):
        if owner_clicked is not True:
            raise PermissionError("Only a deliberate local owner GUI click can enable access")
        if type(seconds) is not int or not 1<=seconds<=SESSION_SECONDS:
            raise ValueError("Unsafe access duration")
        if not isinstance(app_ids,(list,tuple,set,frozenset)) or not 1<=len(app_ids)<=MAX_APPS:
            raise ValueError("No bounded installed application catalog")
        if any(not isinstance(x,str) for x in app_ids):
            raise ValueError("Malformed application catalog")
        approved=frozenset(item for item in app_ids if safe_app_id(item))
        if not approved:
            raise PermissionError("No routine applications are eligible")
        with self._lock:
            self._apps=approved
            self._expires=self.clock()+seconds
            self._left=MAX_ACTIONS
            self._enabled=True
        return len(approved)

    def revoke(self):
        with self._lock:
            self._enabled=False
            self._expires=0.0
            self._left=0
            self._apps=frozenset()

    def status(self):
        with self._lock:
            remaining=self._expires-self.clock()
            active=self._enabled and remaining>0 and self._left>0
            return {
                "active":bool(active),
                "remaining_seconds":max(0,int(remaining)) if active else 0,
                "remaining_actions":self._left if active else 0,
                "eligible_apps":len(self._apps) if active else 0,
                "mode":"routine_apps_only" if active else "off",
            }

    def authorize_service(self,service,action):
        """Only fixed, audited local status adapters are approved automatically."""
        with self._lock:
            if (not self.status()['active'] or
                    service not in ('webbie','nova','onedrive') or
                    action!='status.read'):
                return False
            self._left-=1
            return True

    def authorize(self,action,preview,*,selected_app_id=None):
        """The human approved broad scope, never a particular model command.

        Inspect/focus must retain the existing manually bound exact window.
        This method does NOT grant a new window or bypass X11 safety checks.
        """
        with self._lock:
            if not self.status()["active"] or action not in ROUTINE_ACTIONS:
                return False
            if action in BLOCKED_ACTIONS:
                return False
            if not isinstance(preview,str) or len(preview)>300:
                return False
            if action=="app.open":
                if not preview.startswith("app_id="):
                    return False
                if preview[7:] not in self._apps:
                    return False
            elif action=="keyboard.key":
                # Only harmless navigation keys, never arbitrary keystrokes.
                match=re.fullmatch(
                    r"Press (.+?) in window_id=0x[0-9a-fA-F]{1,16}",preview)
                if not match or match.group(1) not in BENIGN_KEYS:
                    return False
            elif action in ("window.focus","window.target"):
                # Require an explicit existing X11 window selection.
                if not re.search(r"window_id=0x[0-9a-fA-F]{1,16}",preview):
                    return False
                if not safe_app_id(selected_app_id):
                    return False
                if selected_app_id not in self._apps:
                    return False
            elif action in ("observe.apps","observe.windows","task.begin"):
                # The descriptive labels are generated by local operator,
                # not by the LLM. No sensitive window content is stored.
                pass
            else:
                return False
            self._left-=1
            return True
