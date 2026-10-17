"""Verified registry of independently substantial workspace laboratory modules."""
from __future__ import annotations
from . import (max_author,max_study,max_studio,max_media,max_art,max_forage,max_dev,
               max_kali,max_webbie,max_theweb,max_nova,max_comms,max_recovery,max_system,max_backups)

WORKSPACES={
  'Webbie':max_webbie,'The Web':max_theweb,'Studio':max_studio,
  'Media Center':max_media,'BCN / Nova':max_nova,'Author':max_author,
  'Study':max_study,'Art Lab':max_art,'Forage':max_forage,
  'Kali Bay':max_kali,'Dev Bay':max_dev,'Recovery':max_recovery,
  'Communications':max_comms,'System':max_system,'Backups':max_backups,
}

def describe():
    return {name:list(module.ACTIONS) for name,module in WORKSPACES.items()}

def run(workspace,action,root,query=''):
    if workspace not in WORKSPACES:raise ValueError('Unknown workspace')
    mod=WORKSPACES[workspace]
    if action not in mod.ACTIONS:raise ValueError('Operation not available in selected workspace')
    return mod.run(action,root,query)
