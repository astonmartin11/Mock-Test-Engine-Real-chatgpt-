from __future__ import annotations
from database.connection import execute_returning,fetch_all
def add_memory(user_id,subject_id,memory_type,memory_text,topic_id=None,confidence=.6,source_message_id=None): return execute_returning('INSERT INTO tutor_memory(user_id,subject_id,memory_type,topic_id,memory_text,confidence,source_message_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *;',(user_id,subject_id,memory_type,topic_id,memory_text,confidence,source_message_id))
def get_memories(user_id,subject_id,limit=8): return fetch_all('SELECT * FROM tutor_memory WHERE user_id=%s AND subject_id=%s ORDER BY confidence DESC,updated_at DESC LIMIT %s;',(user_id,subject_id,limit))
