"""Backup Lab: read-only owner-selected folder readiness and manifest dry-runs."""
from __future__ import annotations
from collections import Counter,defaultdict
from .max_core import *

def run(action,root,query=''):
    root=selected(root);files=discover(root,limit=350);data={}
    if action=='backup-inventory':data={'files':len(files),'size_bytes':sum(p.stat().st_size for p in files),'no_archive_created':True}
    elif action=='manifest-preview':data={'manifest':[{'file':rel(root,p),'sha256':digest_file(p)} for p in files[:160]], 'not_saved':True}
    elif action=='large-backup-files':data={'files':[{'file':rel(root,p),'size_bytes':p.stat().st_size} for p in sorted(files,key=lambda q:q.stat().st_size,reverse=True)[:80]]}
    elif action=='duplicate-backup-data':
        hashes=defaultdict(list)
        for p in files:
            h=digest_file(p)
            if h:hashes[h].append(rel(root,p))
        data={'exact_duplicates':[v for v in hashes.values() if len(v)>1], 'no_deletions':True}
    elif action=='backup-filetypes':data={'extensions':dict(Counter(p.suffix.lower() for p in files))}
    elif action=='backup-modification-times':data={'items':[{'file':rel(root,p),'mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()} for p in files[:120]]}
    elif action=='excluded-risk-review':
        data={'policy':['Symlink targets are never traversed','Hidden and private credential directories are skipped','Always verify archive and encryption before moving it','No backup destinations are deleted by this tool'], 'files_considered':len(files)}
    elif action=='restore-plan':data={'rehearsal':['Create an approved versioned backup outside the live install','Verify file hashes before restore','Restore into a temporary sandbox only','Compare permissions, paths, and service manifests','Test application data consistency','Document rollback steps','Obtain explicit approval before any live restore'], 'live_restore_performed':False}
    elif action=='core-install-safety':data={'still_blocked':['16 owner-customized source differences in supplied OnePass report','Hardware and speaker validation','Full-system restore rehearsal'], 'install_allowed':False}
    else:raise ValueError('Unsupported Backups operation')
    return standard_result('Backups',action,root,data)
ACTIONS=('backup-inventory','manifest-preview','large-backup-files','duplicate-backup-data','backup-filetypes','backup-modification-times','excluded-risk-review','restore-plan','core-install-safety')
