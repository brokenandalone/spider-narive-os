"""Recovery Workspace: optional private notes audit; no diagnosis or tracking automation."""
from __future__ import annotations
from collections import Counter
from .max_core import *
EXT={'.txt','.md','.markdown','.docx'}

def run(action,root,query=''):
    docs=list(text_records(root,EXT));data={}
    if action=='private-file-inventory':data={'notes':[{'file':n,'word_count':len(WORD.findall(t))} for n,t in docs[:140]], 'content_withheld':True}
    elif action=='reflection-dates':
        pat=r'\b(?:19|20)\d{2}-\d{2}-\d{2}\b'
        data={'date_mentions':sorted({m.group(0) for _,t in docs for m in re.finditer(pat,t)})[:130], 'not_a_sobriety_tracker':True}
    elif action=='meeting-plan-template':data={'fields':['meeting_name','meeting_type','day','time','location_or_link','transportation_plan','support_contact','notes'], 'no_meeting_times_invented':True}
    elif action=='support-plan-template':data={'prompts':['What helps you feel supported?','Who have you chosen to contact when things are difficult?','What safe place can you go to?','What boundaries matter this week?','What would help with routine and rest?'],'no_medical_advice':True}
    elif action=='goals-in-notes':
        data={'goal_markers':[{'file':n,'line':i} for n,t in docs for i,line in enumerate(t.splitlines(),1) if re.search(r'\b(?:goal|plan|next step|intention|hope|meeting)\b',line,re.I)][:140], 'private_content_not_displayed':True}
    elif action=='habit-template':data={'columns':['date','self_selected_routine','completed_optional','private_reflection'], 'no_automatic_notifications':True}
    elif action=='weekly-prompts':data={'prompts':['What felt steady this week?','What made the difficult moments easier?','Which relationships felt supportive?','What did you learn about your boundaries?','What is one realistic next step?'], 'not_diagnostic':True}
    elif action=='privacy-audit':
        data={'local_notes_count':len(docs),'files_read_only':True,'cloud_sync_used':False,'share_actions_available':False}
    elif action=='gentle-reminders':data={'drafts':['Take a moment for a check-in','Remember the meeting you chose to attend','Reach out to someone you trust if it would help'], 'scheduled':False}
    else:raise ValueError('Unsupported Recovery operation')
    return standard_result('Recovery',action,root,data)
ACTIONS=('private-file-inventory','reflection-dates','meeting-plan-template','support-plan-template','goals-in-notes','habit-template','weekly-prompts','privacy-audit','gentle-reminders')
