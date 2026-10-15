"""Kali Bay: offline forensics and security lab paperwork, never launch tools or scans."""
from __future__ import annotations
from collections import defaultdict,Counter
from .max_core import *

def run(action,root,query=''):
    root=selected(root);files=discover(root,limit=500);data={}
    if action=='evidence-manifest':
        data={'files':[{'file':rel(root,p),'sha256':digest_file(p),'bytes':p.stat().st_size} for p in files[:150]],'non_hashable':'None hashes are above the safe size limit'}
    elif action=='size-ledger':data={'files':[{'file':rel(root,p),'bytes':p.stat().st_size} for p in files[:200]]}
    elif action=='timestamp-ledger':
        data={'files':[{'file':rel(root,p),'modified_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()} for p in files[:120]],'warning':'Filesystem timestamps are mutable, not verified incident times.'}
    elif action=='type-survey':data={'types':dict(Counter(p.suffix.lower() or '[none]' for p in files))}
    elif action=='duplicate-evidence':
        groups=defaultdict(list)
        for p in files:
            h=digest_file(p)
            if h:groups[h].append(rel(root,p))
        data={'exact_groups':[{'sha256':h,'files':v} for h,v in groups.items() if len(v)>1]}
    elif action=='chain-preview':
        parent='0'*64;events=[]
        for p in files[:120]:
            h=digest_file(p)
            if not h:continue
            row=rel(root,p);parent=hashlib.sha256((parent+'\x00'+row+'\x00'+h).encode()).hexdigest()
            events.append({'file':row,'sha256':h,'ledger_root':parent})
        data={'chain_entries':events,'final_root':parent,'note':'New unsworn local manifest; not evidence of historical custody.'}
    elif action=='lab-template':
        data={'checklist':['Document owner-approved scope and authorized systems','Record date/time and source','Avoid altering source media','Record hashes before and after analysis','Log tools and versions manually','Separate observation from interpretation','Escalate findings for human review','Preserve original evidence securely'], 'no_scans_executed':True}
    elif action=='ioc-literal-search':
        if not query.strip():raise ValueError('Enter a literal indicator to look for')
        docs=list(text_records(root,{'.txt','.log','.csv','.md','.json'}));q=query.strip().lower()
        data={'matching_files':[n for n,t in docs if q in t.lower()][:100],'no_content_exfiltration':True}
    elif action=='permissions-report':
        data={'world_writable':[rel(root,p) for p in files if p.stat().st_mode&stat.S_IWOTH][:150], 'symlinks_excluded':True}
    else:raise ValueError('Unsupported Kali operation')
    return standard_result('Kali Bay',action,root,data)
ACTIONS=('evidence-manifest','size-ledger','timestamp-ledger','type-survey','duplicate-evidence','chain-preview','lab-template','ioc-literal-search','permissions-report')
