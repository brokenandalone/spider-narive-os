"""Author Workspace: novel, scene, motif and case-file planning audits."""
import re
from collections import Counter
from .max_core import *
EXT={'.md','.txt','.markdown','.docx'}
CHARACTER_NAMES=['Shayna','Eli','Emery','Daniel','Justin','Kayla','Shepherd','Hollow Man','Mercy Man','His Honor','Unbroken']
PLACES=['Mercer','Ninth','Apartment 17','Apt 17','City Hall','Platform Six','Overpass','House of Echoes','Redfield','Thirteen-Mile Road']

def run(action,root,query=''):
    docs=list(text_records(root,EXT));data={}
    if action=='chapter-atlas':
        data={'chapters':[{'file':name,'words':len(WORD.findall(t)),'headings':re.findall(r'^#{1,3}\s+(.+)',t,re.M)[:50],
                           'scenes':len(re.findall(r'^\s*(?:\*\s*\*\s*\*|---)\s*$',t,re.M))+1}
                          for name,t in docs[:120]], 'total_words':sum(len(WORD.findall(t)) for _,t in docs)}
    elif action=='character-mentions':
        names=[n.strip() for n in query.split(',') if n.strip()] if query.strip() else CHARACTER_NAMES
        data={'counts':{n:sum(len(re.findall(r'(?<!\w)'+re.escape(n)+r'(?!\w)',t,re.I)) for _,t in docs) for n in names[:45]},
              'note':'Mentions are not appearances or proof of canon.'}
    elif action=='city-locations':
        data={'locations':{p:[name for name,t in docs if re.search(re.escape(p),t,re.I)][:30] for p in PLACES}}
    elif action=='timeline-clues':
        pat=re.compile(r'\b(?:3:13|13\s*miles?|night\s+\d+|day\s+\d+|20\d{2}|midnight)\b',re.I)
        data={'clues':[{'file':name,'line':i,'text':quote_prefix(line,180)} for name,t in docs for i,line in enumerate(t.splitlines(),1) if pat.search(line)][:180]}
    elif action=='dialogue-density':
        data={'chapters':[{'file':name,'words':len(WORD.findall(t)),'quote_lines':sum(1 for x in t.splitlines() if '"' in x or '“' in x)} for name,t in docs[:120]]}
    elif action=='case-file-index':
        regex=re.compile(r'\b(?:case\s*#?\s*\d+|evidence\s*#?\s*[A-Z]?\d+|\bBCN[- ]?\d+|\b3:13\b)\b',re.I)
        data={'references':[{ 'file':name,'matches':sorted(set(x.group(0) for x in regex.finditer(t)))[:30]} for name,t in docs if regex.search(t)]}
    elif action=='motif-map':
        motifs=['rain','black rain','river','static','streetlight','radio','train','echo','mirror','door','blood','clock']
        data={'motifs':{m:{'total':sum(len(re.findall(r'(?<!\w)'+re.escape(m)+r'(?!\w)',t,re.I)) for _,t in docs),'files':[n for n,t in docs if re.search(re.escape(m),t,re.I)][:15]} for m in motifs}}
    elif action=='draft-flags':
        pat=re.compile(r'\b(?:TODO|FIXME|TBD|\[\s*CHECK[^]]*\]|\[\s*NAME\s*\])\b',re.I)
        data={'flags':[{'file':name,'line':i,'text':quote_prefix(line)} for name,t in docs for i,line in enumerate(t.splitlines(),1) if pat.search(line)][:100]}
    elif action=='scene-flow':
        data={'scenes':[{'file':name,'approximate_scene_words':[len(WORD.findall(x)) for x in re.split(r'^\s*(?:\*\s*\*\s*\*|---)\s*$',t,flags=re.M)][:100]} for name,t in docs[:80]]}
    else:raise ValueError('Unsupported Author operation')
    return standard_result('Author',action,root,data)
ACTIONS=('chapter-atlas','character-mentions','city-locations','timeline-clues','dialogue-density','case-file-index','motif-map','draft-flags','scene-flow')
