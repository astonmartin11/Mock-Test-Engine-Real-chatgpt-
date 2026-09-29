from datetime import datetime,timezone
from utils.hashing import sha256_bytes
from storage.r2 import R2Storage
from database.repositories.documents import DocumentRepository
from database.repositories.chunks import ChunkRepository
from database.connection import execute
from documents.parser import parse_document
from documents.chunker import chunk_pages
from documents.embeddings import embed_texts
from documents.topic_extractor import extract_topics
from ai.providers.gemini import GeminiProvider

def ingest_document(user_id,subject_id,filename,mime_type,data,document_type):
    digest=sha256_bytes(data); docs=DocumentRepository()
    if docs.existing(subject_id,digest): raise ValueError('This document is already indexed for this subject.')
    key=f'users/{user_id}/subjects/{subject_id}/documents/{digest}-{filename}'
    R2Storage().put(key,data,mime_type)
    pages=parse_document(filename,mime_type,data)
    doc=docs.create(user_id=user_id,subject_id=subject_id,document_type=document_type,filename=filename,mime_type=mime_type,storage_provider='r2',storage_key=key,file_size_bytes=len(data),sha256=digest,page_count=len(pages))
    for p in pages:
        execute('INSERT INTO document_pages(document_id,page_number,extracted_text,text_length,has_images,needs_vision) VALUES(%s,%s,%s,%s,%s,%s);',(doc['id'],p.page_number,p.text,len(p.text),p.has_images,p.needs_vision))
    full='\n\n'.join(p.text for p in pages)
    visual_text=''
    if any(p.needs_vision for p in pages) and mime_type=='application/pdf':
        visual_text=GeminiProvider().pdf(data,'Extract academically relevant text, equations, derivations, tables and figure meaning from this PDF. Preserve notation exactly.')
        full+='\n\n'+visual_text
    topics=extract_topics(subject_id,full)
    chunks=chunk_pages(pages)
    if visual_text.strip() and len(full.strip()) > len('\n\n'.join(p.text for p in pages).strip()) + 20:
        # Add Gemini-only extraction as extra RAG material so scanned formulas
        # are not lost merely because local PDF text extraction was sparse.
        from documents.chunker import TextChunk
        base_index = len(chunks)
        extra = [visual_text[i:i+3500] for i in range(0,len(visual_text),3500)]
        chunks.extend(TextChunk(base_index+i, 1, 'Gemini visual extraction', part) for i,part in enumerate(extra) if part.strip())
    vectors=embed_texts([c.content for c in chunks]); repo=ChunkRepository()
    for c,v in zip(chunks,vectors):
        topic_id=None
        for topic in topics:
            if topic['name'].lower() in c.content.lower(): topic_id=str(topic['id']); break
        repo.create({'document_id':doc['id'],'topic_id':topic_id,'chunk_index':c.chunk_index,'title':c.title,'content':c.content,'token_count':max(1,len(c.content)//4),'embedding':v,'metadata':{'page_number':c.page_number,'indexed_at':datetime.now(timezone.utc).isoformat()}})
    docs.mark_complete(str(doc['id']),{'topic_count':len(topics),'chunk_count':len(chunks)})
    return {'document_id':str(doc['id']),'topic_count':len(topics),'chunk_count':len(chunks)}
