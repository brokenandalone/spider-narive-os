"""Webbie Lab: safe assistant content readiness and user-reviewed knowledge planning."""
from __future__ import annotations
from collections import Counter
from .max_core import *
EXT={'.txt','.md','.markdown','.json'}

def run(action,root,query=''):
    docs=list(text_records(root,EXT));data={}
    if action=='knowledge-inventory':data={'documents':[{'file':n,'words':len(WORD.findall(t))} for n,t in docs[:140]], 'note':'Does not import files into running Webbie.'}
    elif action=='learning-topics':
        common=Counter()
        for _,t in docs:common.update(w for w in token_counts(t) if len(w)>8)
        data={'candidate_topics':common.most_common(70),'user_review_required':True}
    elif action=='memory-drift':
        matches=[]
        for n,t in docs:
            for i,line in enumerate(t.splitlines(),1):
                if re.search(r'\b(?:obsolete|superseded|replaced|no longer|outdated|deprecated)\b',line,re.I):matches.append({'file':n,'line':i,'text':quote_prefix(line)})
        data={'possibly_stale_notes':matches[:100]}
    elif action=='command-catalog':
        cmds=['open','search','summarize','research','stop','pause','volume','studio','kali','author','study','media','calendar','browser']
        data={'intents':{c:[n for n,t in docs if re.search(r'\b'+re.escape(c)+r'\b',t,re.I)][:12] for c in cmds},'no_commands_executed':True}
    elif action=='research-backlog':
        data={'questions':[{'file':n,'question':quote_prefix(line,240)} for n,t in docs for line in t.splitlines() if '?' in line][:150]}
    elif action=='safety-intents':
        pat=re.compile(r'\b(?:delete|sudo|password|credential|token|install|publish|send|shutdown|restart)\b',re.I)
        data={'review_locations':[{'file':n,'line':i,'category':'permission_sensitive'} for n,t in docs for i,line in enumerate(t.splitlines(),1) if pat.search(line)][:130], 'source_text_not_commands':True}
    elif action=='voice-phrases':
        data={'wake_word_mention_files':[n for n,t in docs if re.search(r'(?i)\b(?:hey webbie|hey web|wake word|voice profile|speaker)\b',t)], 'no_audio_capture':True}
    elif action=='reference-map':
        data={'references':[{'file':n,'links':len(re.findall(r'https?://',t)),'citations':len(re.findall(r'\[(?:S|\d+)\d*\]',t))} for n,t in docs[:150]]}
    elif action=='assistant-handoff':
        data={'workflow':['Owner queues research in Intelligence Center','Owner chooses documents or explicitly fetches public sources','Local model drafts source-linked summary','Owner reviews citations and approves memory','Separate approved bridge imports result to resident Webbie in future'], 'installed_webbie_unchanged':True}
    else:raise ValueError('Unsupported Webbie Lab operation')
    return standard_result('Webbie',action,root,data)
ACTIONS=('knowledge-inventory','learning-topics','memory-drift','command-catalog','research-backlog','safety-intents','voice-phrases','reference-map','assistant-handoff')
