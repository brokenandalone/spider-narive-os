"""Forage: offline, bounded document research and sourcing without unsupervised web calls."""
from __future__ import annotations
from collections import Counter,defaultdict
from urllib.parse import urlsplit
from .max_core import *
EXT={'.txt','.md','.markdown','.html','.csv','.bib','.docx'}

def run(action,root,query=''):
    docs=list(text_records(root,EXT));q=query.strip();data={}
    if action=='document-corpus':data={'documents':[{'file':n,'words':len(WORD.findall(t)),'sha256_text':hashlib.sha256(t.encode()).hexdigest()} for n,t in docs][:150]}
    elif action=='domain-provenance':
        urls=[x.rstrip('.,;') for _,t in docs for x in re.findall(r'https?://[^\s<>"\)]+',t)]
        groups=defaultdict(list)
        for u in urls:
            try:groups[urlsplit(u).hostname or 'unknown'].append(u)
            except ValueError:continue
        data={'domains':{k:{'references':len(v),'examples':list(dict.fromkeys(v))[:4]} for k,v in sorted(groups.items())[:150]},'not_live_verified':True}
    elif action=='claim-notes':
        data={'candidate_claims':[{'file':n,'line':i,'text':quote_prefix(line,240)} for n,t in docs for i,line in enumerate(t.splitlines(),1) if re.search(r'\b(?:study|reports?|according to|found that|evidence|data show|research)\b',line,re.I)][:140], 'warning':'Language patterns do not establish factual accuracy.'}
    elif action=='term-concordance':
        if not q:raise ValueError('Enter a search phrase to find references')
        data={'hits':[{'file':n,'line':i,'excerpt':quote_prefix(line,230)} for n,t in docs for i,line in enumerate(t.splitlines(),1) if q.lower() in line.lower()][:150]}
    elif action=='research-questions':
        data={'questions':[{'file':n,'text':quote_prefix(line)} for n,t in docs for line in t.splitlines() if '?' in line][:120]}
    elif action=='chronology':
        pat=r'\b(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?\b'
        data={'dates':sorted({m.group(0) for _,t in docs for m in re.finditer(pat,t)})[:150],'note':'Mentions, not publication or verification dates.'}
    elif action=='cross-document-overlap':
        terms=[set(w for w,c in token_counts(t).items() if c>=2 and len(w)>6) for _,t in docs[:60]]
        hits=[]
        for i,(n,_) in enumerate(docs[:60]):
            for j in range(i+1,len(terms)):
                union=terms[i]|terms[j]; overlap=round(len(terms[i]&terms[j])/len(union),3) if union else 0
                if overlap>=.20:hits.append({'pair':[n,docs[j][0]],'shared_keyword_ratio':overlap})
        data={'possible_related_documents':sorted(hits,key=lambda x:x['shared_keyword_ratio'],reverse=True)[:45]}
    elif action=='open-questions':
        notes=[quote_prefix(line) for _,t in docs for line in t.splitlines() if re.search(r'\b(?:unknown|unconfirmed|needs citation|further research|not verified|citation needed)\b',line,re.I)]
        data={'unresolved_notes':notes[:120]}
    elif action=='citation-inventory':
        data={'references':[{'file':n,'citations':len(re.findall(r'\([^()]+,\s*(?:19|20)\d{2}\)',t)),'links':len(re.findall(r'https?://',t))} for n,t in docs[:120]]}
    else:raise ValueError('Unsupported Forage operation')
    return standard_result('Forage',action,root,data)
ACTIONS=('document-corpus','domain-provenance','claim-notes','term-concordance','research-questions','chronology','cross-document-overlap','open-questions','citation-inventory')
