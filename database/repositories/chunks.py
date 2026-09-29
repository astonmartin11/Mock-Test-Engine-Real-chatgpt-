from __future__ import annotations
from database.connection import execute_returning, fetch_all
class ChunkRepository:
    def create(self,row):
        return execute_returning('''INSERT INTO document_chunks (document_id,page_id,topic_id,chunk_index,title,content,chunk_type,token_count,embedding,metadata) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;''', (row['document_id'],row.get('page_id'),row.get('topic_id'),row['chunk_index'],row.get('title'),row['content'],row.get('chunk_type','text'),row.get('token_count'),row.get('embedding'),row.get('metadata',{})))
    def keyword_search(self, subject_id, query, limit=8):
        return fetch_all('''SELECT dc.*, ts_rank(dc.search_vector, plainto_tsquery('english', %s)) AS lexical_score FROM document_chunks dc JOIN documents d ON d.id=dc.document_id WHERE d.subject_id=%s ORDER BY lexical_score DESC LIMIT %s;''', (query,subject_id,limit))
    def vector_search(self, subject_id, embedding, limit=8):
        literal='['+','.join(str(float(x)) for x in embedding)+']'
        return fetch_all('''SELECT dc.*, 1-(dc.embedding <=> %s::vector) AS semantic_score FROM document_chunks dc JOIN documents d ON d.id=dc.document_id WHERE d.subject_id=%s AND dc.embedding IS NOT NULL ORDER BY dc.embedding <=> %s::vector LIMIT %s;''', (literal,subject_id,literal,limit))
