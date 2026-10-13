"""Webbie JARVIS Core: unified owner-approved local tool orchestration.

The owner may grant a STANDING policy, but a model, browser page, terminal
output or arbitrary socket message cannot fabricate an owner command.
Only the native owner GUI calls this dispatcher. All tools here are bounded
read-only evidence providers, not an unrestricted terminal or deployment API.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import threading
import time
from owner_authorization_store import DEFAULT_PATH,read_policy
from jarvis_local_evidence import search_local_evidence,render_evidence
from jarvis_site_audit import inspect_site_project,render_site_report
from jarvis_forage_research import research_public_web,render_public_research
from jarvis_local_site_preview import LocalSitePreview

OPERATIONS=frozenset((
    "local.evidence","site.audit","system.health","project.overview",
    "forage.web","site.preview",
))
MAX_RESULT_LENGTH=8000


@dataclass(frozen=True)
class MissionResult:
    action: str
    status: str
    report: str
    authorized: bool
    read_only: bool=True


class JarvisCore:
    """One active operation, no durable secrets, no model action channel."""

    def __init__(self,*,policy_path=DEFAULT_PATH,
                 evidence=search_local_evidence,site=inspect_site_project,
                 forage=research_public_web,console=None,clock=None,
                 preview=None):
        self.policy_path=Path(policy_path)
        self.evidence=evidence
        self.site=site
        self.forage=forage
        self.console=console
        self.preview=preview or LocalSitePreview()
        self.clock=clock or time.monotonic
        self.lock=threading.RLock()
        self.stop_flag=threading.Event()
        self.active=False
        self.history=[]

    def _permitted(self):
        pref=read_policy(self.policy_path)
        return (pref.get("authorized") is True
                and pref.get("paused") is False)

    def stop(self):
        """STOP revokes local work immediately; output cannot be published."""
        self.stop_flag.set()
        # Shutdown of an existing site is always safe, even during pause.
        self.preview.stop()

    def run(self,action,*,source,folder=None,query=None,home=None):
        if source!="owner_gui" or action not in OPERATIONS:
            return MissionResult(str(action),"denied",
                                 "Only a direct owner GUI mission is accepted.",False)
        if not self._permitted():
            return MissionResult(action,"denied",
                                 "Permanent JARVIS authorization is OFF or paused.",False)
        with self.lock:
            if self.active:
                return MissionResult(action,"busy",
                                     "Another owner mission is active.",True)
            self.active=True
            self.stop_flag.clear()
        try:
            if action=="local.evidence":
                if folder is None or query is None:
                    raise ValueError("Choose a folder and a search phrase")
                data=self.evidence(folder,query,home=home)
                report=render_evidence(data)
            elif action=="site.audit":
                if folder is None:
                    raise ValueError("Choose a local website project folder")
                data=self.site(folder,home=home)
                report=render_site_report(data)
            elif action=="site.preview":
                if folder is None:
                    raise ValueError("Choose a local HTML site folder to preview")
                preview=self.preview.start(folder,home=home)
                report=(
                    "JARVIS · LOCAL STATIC WEBSITE PREVIEW\n"
                    "Preview URL: "+preview["url"]+"\n"
                    "Scope: "+preview["scope"]+"\n"
                    "Only 127.0.0.1 accepts connections. No public deployment, "
                    "site edits, uploads, remote accounts or build scripts.\n"
                    "STOP closes the local preview server.")
            elif action=="forage.web":
                if not query:
                    raise ValueError("Enter a specific public research topic")
                data=self.forage(query)
                report=render_public_research(data)
            elif action=="project.overview":
                if folder is None:
                    raise ValueError("Choose a project folder")
                data=self.evidence(folder,query or "TODO",home=home,
                                   max_results=12)
                report="PROJECT WORK REMINDERS\n"+render_evidence(data)
            else:
                report=self._system_report()
            # Re-check standing access after potentially expensive file I/O.
            if self.stop_flag.is_set() or not self._permitted():
                return MissionResult(action,"canceled",
                                     "STOP/pause revoked this operation. Results discarded.",False)
            answer=MissionResult(action,"observed",report[:MAX_RESULT_LENGTH],True)
            self.history[:]=[{
                "action":action,"result":"observed","read_only":True,
                "time":int(self.clock()),
            }]
            return answer
        except (OSError,ValueError,PermissionError,TypeError) as error:
            return MissionResult(
                action,"failed",
                "JARVIS could not inspect that scope: "+
                str(error)[:180],True)
        finally:
            with self.lock:
                self.active=False

    def _system_report(self):
        from console_bridge import perform_console_request
        checks=(
            "check kernel","check uptime","check memory",
            "check disk space","check webbie service",
            "check nova service","check ollama service",
        )
        lines=["JARVIS · SYSTEM HEALTH · READ ONLY"]
        for check in checks:
            if self.stop_flag.is_set():
                break
            # Explicit internal FIXED diagnostic inventory; no model shell.
            executor=self.console or perform_console_request
            result=executor(check,authorized=True)
            lines.append(str(result or "Unavailable")[:1400])
        lines.append(
            "No packages were installed, services restarted, or settings changed.")
        return "\n\n".join(lines)

    def status(self):
        return {
            "ready":self._permitted(),
            "running":self.active,
            "last_actions":[dict(item) for item in self.history],
            "supported_operations":sorted(OPERATIONS),
            "local_preview":self.preview.status(),
            "can_deploy_website":False,
            "can_run_arbitrary_shell":False,
            "can_run_security_scans":False,
        }
