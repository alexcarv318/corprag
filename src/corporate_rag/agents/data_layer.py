from typing import Any

from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.user import PersistedUser, User


class ProductUserSQLAlchemyDataLayer(SQLAlchemyDataLayer):
    async def _get_user_identifer_by_id(self, user_id: str) -> str:
        return str(user_id)

    async def get_user(self, identifier: str) -> PersistedUser | None:
        result = await self.execute_sql(
            query="""
                SELECT id, username
                FROM users
                WHERE id::text = :identifier OR username = :identifier
            """,
            parameters={"identifier": identifier},
        )
        if not isinstance(result, list) or not result:
            return None

        row = result[0]
        username = str(row["username"])
        return PersistedUser(
            id=str(row["id"]),
            identifier=str(row["id"]),
            createdAt="",
            metadata={"provider": "corporate-rag", "username": username},
            display_name=username,
        )

    async def create_user(self, user: User) -> PersistedUser | None:
        return await self.get_user(user.identifier)

    async def update_thread(
        self,
        thread_id: str,
        name: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        if metadata is None:
            metadata = {}
        metadata = dict(metadata)
        if name is not None:
            metadata["name"] = name
        await super().update_thread(
            thread_id=thread_id,
            name=name,
            user_id=user_id,
            metadata=metadata,
            tags=tags,
        )
