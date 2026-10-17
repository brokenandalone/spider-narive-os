"""Spider Media Center: index, grouping, playback-readiness and sidecar checks."""
from __future__ import annotations
from collections import Counter,defaultdict
from .max_core import *
MUSIC={'.wav','.mp3','.flac','.ogg','.m4a','.aac','.aiff'}
VIDEO={'.mp4','.mkv','.avi','.mov','.webm','.mpeg'}
IMAGE={'.png','.jpg','.jpeg','.gif','.webp','.bmp'}
ALL=MUSIC|VIDEO|IMAGE|{'.srt','.vtt','.nfo','.m3u','.m3u8','.pls'}

def run(action,root,query=''):
    root=selected(root);files=discover(root,ALL);data={}
    if action=='catalog-overview':
        kinds={'music':MUSIC,'video':VIDEO,'images':IMAGE}
        data={'totals':{k:{'count':sum(p.suffix.lower() in exts for p in files),'bytes':sum(p.stat().st_size for p in files if p.suffix.lower() in exts)} for k,exts in kinds.items()}, 'sampled_files':len(files)}
    elif action=='artist-folder-map':
        data={'folders':dict(Counter(str(p.parent.relative_to(root)) for p in files if p.suffix.lower() in MUSIC).most_common(130))}
    elif action=='subtitle-pairing':
        vids=[p for p in files if p.suffix.lower() in VIDEO]
        data={'video_missing_matching_subtitles':[rel(root,p) for p in vids if not any((p.with_suffix(e)).exists() for e in ('.srt','.vtt'))][:140]}
    elif action=='extension-quality':
        data={'formats':dict(Counter(p.suffix.lower() for p in files)), 'nonlossless_audio':sum(p.suffix.lower() in {'.mp3','.m4a','.ogg','.aac'} for p in files),'note':'Codec extension alone does not establish quality.'}
    elif action=='duplicate-titles':
        names=defaultdict(list)
        for p in files:
            if p.suffix.lower() in MUSIC:names[p.stem.casefold()].append(rel(root,p))
        data={'title_collisions':dict((k,v) for k,v in names.items() if len(v)>1),'warning':'Title collisions may be different recordings; no changes made.'}
    elif action=='playlist-suggestion':
        chosen=(query or '').strip().casefold()
        tracks=[rel(root,p) for p in files if p.suffix.lower() in MUSIC and (not chosen or chosen in p.stem.casefold())]
        data={'preview_entries':tracks[:300],'m3u8_lines':['#EXTM3U']+tracks[:300], 'export':'Not saved. Copy or export explicitly; never autoplay.'}
    elif action=='big-media':
        data={'files':[{'path':rel(root,p),'size_bytes':p.stat().st_size} for p in sorted(files,key=lambda p:p.stat().st_size,reverse=True)[:75]]}
    elif action=='video-series-map':
        rx=re.compile(r'(?i)\bS(\d{1,2})E(\d{1,3})\b')
        data={'recognized_episodes':[{'file':rel(root,p),'season':int(m.group(1)),'episode':int(m.group(2))} for p in files if p.suffix.lower() in VIDEO if (m:=rx.search(p.stem))][:200]}
    elif action=='nfo-artwork-pairing':
        dirs=defaultdict(set)
        for p in files:dirs[str(p.parent.relative_to(root))].add(p.suffix.lower())
        data={'folders_missing_art':[k for k,v in dirs.items() if (v&MUSIC or v&VIDEO) and not v&IMAGE][:100]}
    else:raise ValueError('Unsupported Media operation')
    return standard_result('Media Center',action,root,data)
ACTIONS=('catalog-overview','artist-folder-map','subtitle-pairing','extension-quality','duplicate-titles','playlist-suggestion','big-media','video-series-map','nfo-artwork-pairing')
