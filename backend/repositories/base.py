from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import Base


class BaseRepository[ModelType: Base]:
    """Generic repository base class implementing common database CRUD operations."""

    def __init__(self, model: type[ModelType], db_session: AsyncSession) -> None:
        """Initializes the repository with a specific model and session.

        Args:
            model: The SQLAlchemy model class.
            db_session: The active async database session.
        """
        self.model = model
        self.db_session = db_session

    async def get(self, entity_id: UUID) -> ModelType | None:
        """Retrieves a single entity by its primary key ID.

        Args:
            entity_id: The UUID of the entity.

        Returns:
            ModelType | None: The entity instance or None if not found.
        """
        return await self.db_session.get(self.model, entity_id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Retrieves a list of entities with pagination support.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence[ModelType]: List of found entity instances.
        """
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def create(self, obj_in: dict[str, Any] | ModelType) -> ModelType:
        """Creates and persists a new entity instance.

        Args:
            obj_in: A dictionary of attributes or an instantiated model object.

        Returns:
            ModelType: The created and flushed model instance.
        """
        db_obj = self.model(**obj_in) if isinstance(obj_in, dict) else obj_in
        self.db_session.add(db_obj)
        await self.db_session.flush()
        return db_obj

    async def update(
        self, db_obj: ModelType, obj_in: dict[str, Any] | ModelType
    ) -> ModelType:
        """Updates an existing entity instance with new attributes.

        Args:
            db_obj: The existing database model instance to update.
            obj_in: A dictionary of changes or another model
                instance containing updates.

        Returns:
            ModelType: The updated and flushed model instance.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = {
                key: val
                for key, val in obj_in.__dict__.items()
                if not key.startswith("_")
            }

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.db_session.add(db_obj)
        await self.db_session.flush()
        return db_obj

    async def delete(self, entity_id: UUID) -> ModelType | None:
        """Deletes an entity instance by ID.

        Args:
            entity_id: The primary key UUID of the entity.

        Returns:
            ModelType | None: The deleted model instance or None if not found.
        """
        db_obj = await self.get(entity_id)
        if db_obj:
            await self.db_session.delete(db_obj)
            await self.db_session.flush()
        return db_obj
