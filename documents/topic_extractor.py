from __future__ import annotations
import re
from ai.router import AIRouter
from ai.schemas import TopicExtraction
from ai.prompts.document import DOCUMENT_SYSTEM,TOPIC_EXTRACTION_PROMPT
from database.repositories.topics import TopicRepository

def _norm(name: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',name.lower()).strip()

def extract_topics(subject_id: str,document_text: str):
    sample=document_text[:12000]
    result=AIRouter().structured('TOPIC_EXTRACTION',TOPIC_EXTRACTION_PROMPT.format(document_text=sample),TopicExtraction,DOCUMENT_SYSTEM,max_tokens=1800)
    repo=TopicRepository(); stored=[]
    # parents first
    parent_ids={}
    for item in result.topics:
        parent=str(item.get('parent_topic') or '').strip()
        if parent and parent not in parent_ids:
            row=repo.create(subject_id,parent,_norm(parent))
            parent_ids[parent]=str(row['id'])
    for item in result.topics:
        name=str(item.get('name') or '').strip()
        if not name: continue
        parent=str(item.get('parent_topic') or '').strip()
        row=repo.create(subject_id,name,_norm(name),parent_ids.get(parent),str(item.get('description') or '') or None,float(item.get('weight') or 1.0))
        stored.append(row)
    return stored
