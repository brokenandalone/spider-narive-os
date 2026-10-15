"""System Bay: project/config review only, no running package or service changes."""
from __future__ import annotations
from collections import Counter
from .max_core import *
EXT={'.service','.timer','.desktop','.ini','.conf','.json','.yaml','.yml','.toml','.sh','.md','.txt'}

def run(action,root,query=''):
    root=selected(root);docs=list(text_records(root,EXT));data={}
    if action=='config-inventory':data={'files':[n for n,_ in docs][:180], 'counts':dict(Counter(Path(n).suffix for n,_ in docs))}
    elif action=='service-declarations':data={'service_unit_candidates':[n for n,_ in docs if n.endswith(('.service','.timer'))][:150], 'running_services_not_changed':True}
    elif action=='hardcoded-paths':
        data={'absolute_path_lines':[{'file':n,'line':i} for n,t in docs for i,line in enumerate(t.splitlines(),1) if re.search(r'(?<!\w)/(?:home|usr|opt|etc|var)/',line)][:120], 'values_withheld':True}
    elif action=='release-notes':data={'release_documents':[n for n,_ in docs if re.search(r'(?i)(?:release|upgrade|changelog|install)',n)][:150]}
    elif action=='autostart-survey':data={'autostart_candidates':[n for n,_ in docs if 'autostart' in n.lower() or n.endswith('.service')], 'no_autostart_changed':True}
    elif action=='unsafe-script-indicators':
        pat=re.compile(r'(?i)(?:rm\s+-rf|curl[^\n|]*\|\s*(?:ba)?sh|chmod\s+777|sudo\s+.*install)')
        data={'review_locations':[{'file':n,'line':i} for n,t in docs for i,line in enumerate(t.splitlines(),1) if pat.search(line)][:130], 'values_not_displayed':True}
    elif action=='local-version-hints':data={'version_mentions':[{'file':n,'count':len(re.findall(r'\b\d+\.\d+(?:\.\d+)?\b',t))} for n,t in docs[:130]]}
    elif action=='backup-candidates':data={'project_files':len(docs),'estimated_bytes':sum(len(t.encode()) for _,t in docs),'backup_not_created':True}
    elif action=='release-gate-template':
        data={'gates':['Owner-source reconciliation','No pending semantic conflicts','Real GUI and microphone acceptance','Cory/Shayna speaker verification','Live Kali tests with authorization','Nova/radio separation','Backup, restore drill, rollback','Explicit owner approval for exact install commit'], 'installation_locked':True}
    else:raise ValueError('Unsupported System operation')
    return standard_result('System',action,root,data)
ACTIONS=('config-inventory','service-declarations','hardcoded-paths','release-notes','autostart-survey','unsafe-script-indicators','local-version-hints','backup-candidates','release-gate-template')
