"""Spider Studio: track planning, WAV checks and album consistency reports."""
from __future__ import annotations
import wave, math
from collections import Counter,defaultdict
from .max_core import *
AUDIO={'.wav','.mp3','.flac','.ogg','.m4a','.aiff','.aif'}

def run(action,root,query=''):
    root=selected(root);files=discover(root,AUDIO);data={}
    if action=='session-inventory':
        data={'tracks':[{'file':rel(root,p),'bytes':p.stat().st_size,'extension':p.suffix.lower()} for p in files[:300]],'count':len(files)}
    elif action in ('wav-technical','album-consistency','duration-ledger','stereo-readiness'):
        items=[]
        for p in files:
            if p.suffix.lower()!='.wav':continue
            try:
                with wave.open(str(p),'rb') as f:
                    item={'file':rel(root,p),'channels':f.getnchannels(),'rate_hz':f.getframerate(),
                         'sample_bits':f.getsampwidth()*8,'frames':f.getnframes(),
                         'seconds':round(f.getnframes()/max(1,f.getframerate()),2)}
                    items.append(item)
            except (wave.Error,EOFError,OSError):items.append({'file':rel(root,p),'error':'Unreadable standard PCM WAV header'})
        if action=='album-consistency':
            ok=[x for x in items if 'rate_hz' in x];keys=[(x['rate_hz'],x['sample_bits'],x['channels']) for x in ok]
            data={'common_formats':[{ 'format':str(k),'tracks':v} for k,v in Counter(keys).most_common()], 'mixed_formats':len(set(keys))>1,'unreadable':len(items)-len(ok)}
        elif action=='stereo-readiness':
            data={'mono':[x['file'] for x in items if x.get('channels')==1], 'multichannel':[x['file'] for x in items if x.get('channels',0)>2], 'stereo':[x['file'] for x in items if x.get('channels')==2]}
        elif action=='duration-ledger':data={'tracks':items,'total_seconds':round(sum(x.get('seconds',0) for x in items),2)}
        else:data={'headers':items}
    elif action=='take-groups':
        def group(p):return re.sub(r'(?i)[_ .-]*(?:take|tk|v|version|mix)[_ .-]*\d+','',p.stem).lower()
        names=defaultdict(list)
        for p in files:names[group(p)].append(rel(root,p))
        data={'possible_takes':dict((k,v) for k,v in names.items() if len(v)>1),'heuristic_only':True}
    elif action=='studio-todos':
        docs=list(text_records(root,{'.txt','.md'}))
        data={'production_notes':[{'file':n,'line':i,'text':quote_prefix(line)} for n,t in docs for i,line in enumerate(t.splitlines(),1) if re.search(r'(?i)\b(?:mix|master|retake|vocals|stem|tempo|producer|session|record|mic)\b',line)][:130]}
    elif action=='mix-delivery-checklist':
        data={'checklist':['Save source session in project folder','Archive source takes and tempo map','Confirm sample rate and bit depth for delivery','Check clipping and headroom','Listen through fade boundaries','Check mono compatibility','Export an approved reference mix','Record ISRC and final version name','Back up stems and final master'],'changes_made':False}
    elif action=='track-names':
        data={'titles':sorted(set(p.stem for p in files),key=str.casefold)[:300], 'count':len(files)}
    elif action=='exact-duplicates':
        size_map=defaultdict(list)
        for p in files:size_map[p.stat().st_size].append(p)
        groups=defaultdict(list)
        for batch in size_map.values():
            if len(batch)<2:continue
            for p in batch:
                d=digest_file(p)
                if d:groups[d].append(rel(root,p))
        data={'duplicates':[{'sha256':h,'files':v} for h,v in groups.items() if len(v)>1]}
    else:raise ValueError('Unsupported Studio operation')
    return standard_result('Studio',action,root,data)
ACTIONS=('session-inventory','wav-technical','album-consistency','duration-ledger','stereo-readiness','take-groups','studio-todos','mix-delivery-checklist','track-names','exact-duplicates')
