"""Communications: offline review of selected drafts. Never sends messages."""
from __future__ import annotations
from collections import Counter
from .max_core import *
EXT={'.txt','.md','.markdown','.docx'}

def run(action,root,query=''):
    docs=list(text_records(root,EXT));data={}
    if action=='draft-catalog':data={'drafts':[{'file':n,'words':len(WORD.findall(t))} for n,t in docs[:150]]}
    elif action=='message-lengths':data={'messages':[{'file':n,'characters':len(t),'estimated_sms_segments':(len(t)+159)//160} for n,t in docs[:120]], 'estimate_is_plain_text_only':True}
    elif action=='subject-lines':data={'first_lines':[{'file':n,'preview':quote_prefix(t.splitlines()[0])} for n,t in docs if t.splitlines()][:125]}
    elif action=='tone-flags':
        words=['urgent','immediately','guaranteed','ASAP','never','always','final notice']
        data={'flags':{w:[n for n,t in docs if w.lower() in t.lower()][:35] for w in words}, 'no_tone_judgment':True}
    elif action=='placeholder-check':
        pat=re.compile(r'\{\{[^}]+\}\}|\[[A-Z_ ]{3,}\]')
        data={'placeholders':[{'file':n,'tokens':sorted(set(m.group(0) for m in pat.finditer(t)))[:30]} for n,t in docs if pat.search(t)]}
    elif action=='url-inventory':data={'urls':[{'file':n,'count':len(re.findall('https?://',t))} for n,t in docs]}
    elif action=='confidentiality-review':
        pat=re.compile(r'\b(?:password|social security|ssn|api[_ -]?key|access token|private key|credit card)\b',re.I)
        data={'sensitive_term_locations':[{'file':n,'line':i} for n,t in docs for i,line in enumerate(t.splitlines(),1) if pat.search(line)][:100], 'values_never_returned':True}
    elif action=='announcement-readiness':data={'checklist':['Confirm intended audience','Verify facts and dates','Proofread names and URLs','Confirm attachments authorized to share','Review personal information','Approve final wording','Send manually through separately connected service'], 'sent':False}
    elif action=='response-prompt':
        data={'draft_prompts':[f'What outcome should this message achieve: {query.strip() or "your topic"}?','What does the recipient need to know?','Which facts can you verify?','What clear action should they take?','Does the tone match the relationship?'],'messages_sent':0}
    else:raise ValueError('Unsupported Communications operation')
    return standard_result('Communications',action,root,data)
ACTIONS=('draft-catalog','message-lengths','subject-lines','tone-flags','placeholder-check','url-inventory','confidentiality-review','announcement-readiness','response-prompt')
