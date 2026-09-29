from __future__ import annotations
from database.repositories.subjects import SubjectRepository

def active_subject(user_id: str):
    repo = SubjectRepository()
    rows = repo.list_for_user(user_id)
    if rows:
        return rows[0]
    return repo.create(user_id, 'Engineering')
