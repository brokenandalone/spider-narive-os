"""Study Workspace: owner-provided local coursework review, never auto-submission."""
import re
from collections import Counter
from .max_core import *
EXT={'.txt','.md','.markdown','.bib','.docx'}

def run(action,root,query=''):
    docs=list(text_records(root,EXT));joined='\n'.join(t for _,t in docs);data={}
    if action=='course-map':
        data={'courses':dict(Counter(x.upper() for x in re.findall(r'\b(?:PSY|SOC|ENG|HUM|MAT)[- ]?\d{3}\b',joined,re.I))), 'documents':len(docs)}
    elif action=='rubric-terms':
        terms=[x.strip() for x in query.split(',') if x.strip()]
        if not terms:terms=['analyze','evaluate','compare','evidence','citation','reflection','social','psychological','culture','ethical']
        data={'terms':{term:sum(len(re.findall(re.escape(term),t,re.I)) for _,t in docs) for term in terms[:35]}, 'not_a_grading_assessment':True}
    elif action=='apa-check':
        data={'documents':[{'file':name,'author_year_citations':len(re.findall(r'\([A-Z][\w\s,&.-]+,\s*(?:19|20)\d{2}\)',t)),
             'doi_mentions':len(re.findall(r'(?:doi:|doi\.org/)',t,re.I)), 'references_heading':bool(re.search(r'^\s*References\s*$',t,re.M|re.I))} for name,t in docs[:100]]}
    elif action=='study-glossary':
        data={'terms':dict(Counter(w.lower() for w in WORD.findall(joined) if len(w)>=9).most_common(55))}
    elif action=='task-markers':
        data={'tasks':[{'file':n,'line':i,'text':quote_prefix(line)} for n,t in docs for i,line in enumerate(t.splitlines(),1) if re.search(r'\b(?:TODO|read|submit|quiz|discussion|milestone|due)\b',line,re.I)][:120]}
    elif action=='reading-load':
        data={'documents':[{'file':n,'words':len(WORD.findall(t)), 'estimated_minutes_at_200_wpm':round(len(WORD.findall(t))/200,1)} for n,t in docs[:100]]}
    elif action=='outline-check':
        data={'documents':[{'file':n,'headings':re.findall(r'^#{1,5}\s+(.+)',t,re.M)[:30], 'paragraphs':sum(1 for p in re.split(r'\n\s*\n',t) if p.strip())} for n,t in docs[:100]]}
    elif action=='source-ledger':
        urls=re.findall(r'https?://[^\s<>"\)]+',joined)
        data={'distinct_sources':list(dict.fromkeys(urls))[:130], 'mentions':len(urls),'verification':'Links are extracted, not visited or validated.'}
    elif action=='reflection-prompts':
        chosen=query.strip() or 'the central idea in your coursework'
        data={'prompts':[f'What evidence supports {chosen}?',f'What social context affects {chosen}?',f'Which assumptions about {chosen} need checking?',f'What counterargument matters most?',f'How would this apply to a real case?'], 'no_answers_generated':True}
    else:raise ValueError('Unsupported Study operation')
    return standard_result('Study',action,root,data)
ACTIONS=('course-map','rubric-terms','apa-check','study-glossary','task-markers','reading-load','outline-check','source-ledger','reflection-prompts')
