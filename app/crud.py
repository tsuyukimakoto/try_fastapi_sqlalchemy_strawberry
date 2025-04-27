from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
from typing import List, Optional


async def get_item(db: AsyncSession, item_id: int) -> Optional[models.Item]:
    result = await db.execute(select(models.Item).where(models.Item.id == item_id))
    return result.scalars().first()


async def get_items(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Item]:
    result = await db.execute(select(models.Item).offset(skip).limit(limit))
    return result.scalars().all()


async def create_item(db: AsyncSession, item: schemas.ItemCreate) -> models.Item:
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    db_item = await get_item(db, item_id)
    if db_item:
        await db.delete(db_item)
        await db.commit()
        return True
    return False


async def update_item(db: AsyncSession, item_id: int, item_update: schemas.ItemCreate) -> Optional[models.Item]:
    db_item = await get_item(db, item_id)
    if db_item:
        update_data = item_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)
        await db.commit()
        await db.refresh(db_item)
        return db_item
    return None

