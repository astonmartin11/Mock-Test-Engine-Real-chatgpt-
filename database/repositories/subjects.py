from __future__ import annotations

from typing import Any

from database.connection import execute_returning, fetch_all, fetch_one


class SubjectRepository:

    def create(
        self,
        user_id: str,
        name: str,
        code: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        return execute_returning(
            '''
            INSERT INTO subjects (
                user_id,
                name,
                code,
                description
            )
            VALUES (%s, %s, %s, %s)
            RETURNING *;
            ''',
            (user_id, name, code, description),
        )

    def get(
        self,
        subject_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        return fetch_one(
            '''
            SELECT *
            FROM subjects
            WHERE id = %s
              AND user_id = %s
            LIMIT 1;
            ''',
            (subject_id, user_id),
        )

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return fetch_all(
            '''
            SELECT *
            FROM subjects
            WHERE user_id = %s
            ORDER BY active DESC, created_at ASC;
            ''',
            (user_id,),
        )

    def rename(
        self,
        subject_id: str,
        user_id: str,
        name: str,
    ) -> dict[str, Any]:
        return execute_returning(
            '''
            UPDATE subjects
            SET name = %s
            WHERE id = %s
              AND user_id = %s
            RETURNING *;
            ''',
            (name, subject_id, user_id),
        )

    def delete(
        self,
        subject_id: str,
        user_id: str,
    ) -> None:
        # ON DELETE CASCADE handles dependent subject-scoped rows.
        from database.connection import execute

        execute(
            '''
            DELETE FROM subjects
            WHERE id = %s
              AND user_id = %s;
            ''',
            (subject_id, user_id),
        )

    def count(self) -> int:
        row = fetch_one("SELECT COUNT(*) AS count FROM subjects;")
        return int(row["count"]) if row else 0
