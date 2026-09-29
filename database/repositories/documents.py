from __future__ import annotations
from typing import Any
from database.connection import execute, execute_returning, fetch_all, fetch_one

class DocumentRepository:
    def existing(self, subject_id, sha256):
        return fetch_one('SELECT * FROM documents WHERE subject_id=%s AND sha256=%s LIMIT 1;', (subject_id, sha256))
    def create(self, **kwargs):
        return execute_returning('''INSERT INTO documents (user_id,subject_id,document_type,filename,mime_type,storage_provider,storage_key,file_size_bytes,sha256,page_count) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *;''', tuple(kwargs[k] for k in ['user_id','subject_id','document_type','filename','mime_type','storage_provider','storage_key','file_size_bytes','sha256','page_count']))
    def mark_complete(self, document_id, metadata):
        import json
        return execute_returning('''UPDATE documents SET processing_status='completed', extracted_text_available=TRUE, embedding_processed=TRUE, processed_at=NOW(), metadata=metadata || %s::jsonb WHERE id=%s RETURNING *;''', (json.dumps(metadata), document_id))
    def list_for_subject(self, subject_id):
        return fetch_all('SELECT * FROM documents WHERE subject_id=%s ORDER BY created_at DESC;', (subject_id,))
