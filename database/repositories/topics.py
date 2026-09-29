from __future__ import annotations

from typing import Any

from database.connection import execute_returning, fetch_all, fetch_one


class TopicRepository:

    def create(
        self,
        subject_id: str,
        name: str,
        normalized_name: str,
        parent_topic_id: str | None = None,
        description: str | None = None,
        syllabus_weight: float = 1.0,
    ) -> dict[str, Any]:
        return execute_returning(
            '''
            INSERT INTO topics (
                subject_id,
                parent_topic_id,
                name,
                normalized_name,
                description,
                syllabus_weight
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (subject_id, normalized_name)
            DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                syllabus_weight = EXCLUDED.syllabus_weight
            RETURNING *;
            ''',
            (
                subject_id,
                parent_topic_id,
                name,
                normalized_name,
                description,
                syllabus_weight,
            ),
        )

    def list_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        return fetch_all(
            '''
            SELECT *
            FROM topics
            WHERE subject_id = %s
            ORDER BY name;
            ''',
            (subject_id,),
        )

    def get(self, topic_id: str) -> dict[str, Any] | None:
        return fetch_one(
            '''
            SELECT *
            FROM topics
            WHERE id = %s
            LIMIT 1;
            ''',
            (topic_id,),
        )

    def count(self) -> int:
        row = fetch_one("SELECT COUNT(*) AS count FROM topics;")
        return int(row["count"]) if row else 0
