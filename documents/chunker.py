from __future__ import annotations
from dataclasses import dataclass

@dataclass
class TextChunk:
    chunk_index: int
    page_number: int
    title: str
    content: str
    chunk_type: str = 'text'

def _split(text: str,max_chars: int=3500):
    text=text.strip()
    if not text: return []
    parts=[p.strip() for p in text.split('\n\n') if p.strip()]
    chunks=[]; current=''
    for p in parts:
        if not current or len(current)+len(p)+2<=max_chars:
            current=p if not current else current+'\n\n'+p
        else:
            chunks.append(current); current=p
    if current: chunks.append(current)
    out=[]
    for c in chunks:
        if len(c)<=max_chars: out.append(c)
        else:
            out.extend(c[i:i+max_chars] for i in range(0,len(c),max_chars))
    return out

def chunk_pages(pages):
    out=[]; idx=0
    for p in pages:
        for c in _split(p.text):
            out.append(TextChunk(idx,p.page_number,f'Page {p.page_number}',c)); idx+=1
    return out
