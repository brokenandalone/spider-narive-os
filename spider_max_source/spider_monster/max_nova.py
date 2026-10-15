"""BCN Radio / Nova: offline program planning and library sanity only."""
from __future__ import annotations
from collections import Counter,defaultdict
from .max_core import *
MUSIC={'.wav','.mp3','.flac','.ogg','.m4a'}

def run(action,root,query=''):
    root=selected(root);files=discover(root,MUSIC);data={}
    if action=='radio-catalog':data={'tracks':[{'file':rel(root,p),'bytes':p.stat().st_size} for p in files[:350]]}
    elif action=='title-collisions':
        titles=defaultdict(list)
        for p in files:titles[p.stem.casefold()].append(rel(root,p))
        data={'same_title':{k:v for k,v in titles.items() if len(v)>1},'not_deletion_candidates':True}
    elif action=='artist-folders':data={'folders':dict(Counter(str(p.parent.relative_to(root)) for p in files).most_common(160))}
    elif action=='onair-readiness':data={'tracks':len(files),'empty_tracks':[rel(root,p) for p in files if p.stat().st_size==0], 'nothing_sent_to_broadcaster':True}
    elif action=='format-coverage':data={'extensions':dict(Counter(p.suffix.lower() for p in files))}
    elif action=='airplay-log-template':data={'fields':['timestamp_local','source_file','approved_artist','approved_title','runtime_seconds','transition','voice_break_id','license_review'], 'no_real_airplay_logs_accessed':True}
    elif action=='duplicate-audio':
        buckets=defaultdict(list)
        for p in files:
            h=digest_file(p)
            if h:buckets[h].append(rel(root,p))
        data={'exact_audio_duplicates':[v for v in buckets.values() if len(v)>1]}
    elif action=='transition-plan':data={'checklist':['Verify voice-break file exists and decodes','Confirm track duration and station fallback','Check crossfade is bounded by track lengths','Test ducks/restores on isolated offline render','Verify output stream with broadcaster disconnected','Check logs for stale file paths','Review changes before any restart'], 'broadcasting_untouched':True}
    elif action=='playlist-preview':
        chosen=query.strip().lower()
        data={'preview':sorted([rel(root,p) for p in files if not chosen or chosen in p.stem.lower()],key=str.lower)[:200], 'not_queued_or_transmitted':True}
    else:raise ValueError('Unsupported Nova operation')
    return standard_result('BCN / Nova',action,root,data)
ACTIONS=('radio-catalog','title-collisions','artist-folders','onair-readiness','format-coverage','airplay-log-template','duplicate-audio','transition-plan','playlist-preview')
