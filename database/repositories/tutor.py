from __future__ import annotations
from database.connection import execute,execute_returning,fetch_all
class TutorRepository:
    def create_conversation(self,user_id,subject_id,title=None): return execute_returning('INSERT INTO tutor_conversations(user_id,subject_id,title) VALUES(%s,%s,%s) RETURNING *;',(user_id,subject_id,title))
    def add_message(self,conversation_id,role,content,model=None,token_estimate=None):
        row=execute_returning('INSERT INTO tutor_messages(conversation_id,role,content,model,token_estimate) VALUES(%s,%s,%s,%s,%s) RETURNING *;',(conversation_id,role,content,model,token_estimate)); execute('UPDATE tutor_conversations SET updated_at=NOW() WHERE id=%s;',(conversation_id,)); return row
    def recent(self,conversation_id,limit=8): return fetch_all('SELECT * FROM tutor_messages WHERE conversation_id=%s ORDER BY created_at DESC LIMIT %s;',(conversation_id,limit))
