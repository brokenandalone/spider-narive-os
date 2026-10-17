"""The Web desktop: user-selected .desktop / KDE launcher and wallpaper audits."""
from __future__ import annotations
import configparser
from collections import Counter
from .max_core import *
EXT={'.desktop','.ini','.conf','.json','.png','.jpg','.jpeg','.webp','.svg'}

def entries(root):
    for p in discover(root,{'.desktop'}):
        parser=configparser.ConfigParser(interpolation=None,strict=False)
        try:parser.read(p,encoding='utf-8')
        except (OSError,configparser.Error):continue
        if 'Desktop Entry' not in parser:continue
        d=parser['Desktop Entry']
        yield rel(root,p), {'name':d.get('Name',''),'type':d.get('Type',''),
                           'exec_declared':bool(d.get('Exec','')), 'icon_declared':bool(d.get('Icon','')),
                           'terminal':d.get('Terminal','false'),'categories':d.get('Categories',''),
                           'hidden':d.get('Hidden','false'),'nodisplay':d.get('NoDisplay','false')}

def run(action,root,query=''):
    root=selected(root);items=list(entries(root));data={}
    if action=='launcher-catalog':data={'launchers':[{ 'file':n, **e} for n,e in items[:180]], 'never_executed':True}
    elif action=='launcher-health':data={'missing_exec':[n for n,e in items if e['type']=='Application' and not e['exec_declared']], 'missing_icons':[n for n,e in items if not e['icon_declared']]}
    elif action=='launcher-duplicates':
        names=Counter(e['name'].casefold() for _,e in items)
        data={'duplicate_labels':[n for n,c in names.items() if c>1]}
    elif action=='desktop-menu':data={'visible':[e['name'] for _,e in items if e['hidden']!='true' and e['nodisplay']!='true'][:180]}
    elif action=='desktop-categories':data={'categories':dict(Counter(category for _,e in items for category in e['categories'].split(';') if category))}
    elif action=='wallpaper-index':data={'wallpapers':[rel(root,p) for p in discover(root,{'.png','.jpg','.jpeg','.webp','.svg'})][:220]}
    elif action=='desktop-theme-inventory':data={'theme_candidates':[rel(root,p) for p in discover(root,{'.ini','.json','.conf'}) if re.search(r'(?i)\b(?:theme|appearance|color|plasma|kde)\b',p.name)][:100]}
    elif action=='desktop-registry':
        expected=['Studio','Study','Author','Recovery','Art','Kali','Dev','Webbie','Media','Forage']
        data={'workspace_labels':{x:[n for n,e in items if x.lower() in e['name'].lower()][:20] for x in expected}}
    elif action=='shell-test-plan':data={'manual_tests':['KDE panel and task manager appear','All workspace tabs open and can close','Display scaling and wallpaper load','Webbie voice service stays active','Studio and Author open correct apps','Notifications and quick settings show','No unauthorized control executes'], 'tests_not_run':True}
    else:raise ValueError('Unsupported The Web operation')
    return standard_result('The Web',action,root,data)
ACTIONS=('launcher-catalog','launcher-health','launcher-duplicates','desktop-menu','desktop-categories','wallpaper-index','desktop-theme-inventory','desktop-registry','shell-test-plan')
