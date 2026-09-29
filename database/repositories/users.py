from __future__ import annotations

from typing import Any

from database.connection import execute_returning, fetch_all, fetch_one


class UserRepository:

    def get_by_auth(
        self,
        auth_provider: str,
        auth_subject: str,
    ) -> dict[str, Any] | None:
        return fetch_one(
            '''
            SELECT *
            FROM users
            WHERE auth_provider = %s
              AND auth_subject = %s
            LIMIT 1;
            ''',
            (auth_provider, auth_subject),
        )

    def create(
        self,
        auth_provider: str,
        auth_subject: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        return execute_returning(
            '''
            INSERT INTO users (
                auth_provider,
                auth_subject,
                email,
                display_name
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (auth_provider, auth_subject)
            DO UPDATE SET
                email = EXCLUDED.email,
                display_name = EXCLUDED.display_name,
                updated_at = NOW()
            RETURNING *;
            ''',
            (
                auth_provider,
                auth_subject,
                email,
                display_name,
            ),
        )

    def list_active(self) -> list[dict[str, Any]]:
        return fetch_all(
            '''
            SELECT *
            FROM users
            WHERE is_active = TRUE
            ORDER BY created_at DESC;
            '''
        )

    def count(self) -> int:
        row = fetch_one("SELECT COUNT(*) AS count FROM users;")
        return int(row["count"]) if row else 0
