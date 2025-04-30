from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from . import models, schemas
from typing import List, Optional
import base64


# --- Item CRUD ---

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


# --- User CRUD ---

async def get_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    result = await db.execute(
        select(models.User)
        .where(models.User.username == username)
        .options(selectinload(models.User.credentials)) # Eager load credentials
    )
    return result.scalars().first()


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    db_user = models.User(username=user.username, display_name=user.display_name)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


# --- Credential CRUD ---

async def add_credential_to_user(
    db: AsyncSession,
    user: models.User,
    credential_id_b64: schemas.Base64UrlStr, # Base64URL encoded string
    public_key_b64: schemas.Base64UrlStr,   # Base64URL encoded string
    sign_count: int,
    transports: Optional[List[str]] = None
) -> models.Credential:
    credential_id_bytes = base64.urlsafe_b64decode(credential_id_b64 + '==')
    public_key_bytes = base64.urlsafe_b64decode(public_key_b64 + '==')

    db_credential = models.Credential(
        user_id=user.id,
        credential_id=credential_id_bytes,
        public_key=public_key_bytes,
        sign_count=sign_count,
        transports=transports
    )
    db.add(db_credential)
    await db.commit()
    await db.refresh(db_credential)
    return db_credential

async def get_credentials_by_user(db: AsyncSession, user_id: int) -> List[models.Credential]:
    result = await db.execute(
        select(models.Credential).where(models.Credential.user_id == user_id)
    )
    return result.scalars().all()

async def get_credential_by_id(db: AsyncSession, credential_id_b64: schemas.Base64UrlStr) -> Optional[models.Credential]:
    credential_id_bytes = base64.urlsafe_b64decode(credential_id_b64 + '==')
    result = await db.execute(
        select(models.Credential)
        .where(models.Credential.credential_id == credential_id_bytes)
        .options(selectinload(models.Credential.user)) # Eager load user
    )
    return result.scalars().first()

async def update_credential_sign_count(db: AsyncSession, credential: models.Credential, new_sign_count: int) -> models.Credential:
    credential.sign_count = new_sign_count
    await db.commit()
    await db.refresh(credential)
    return credential
