from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, AsyncGenerator
from contextlib import asynccontextmanager

from . import crud, models, schemas, database
from .database import engine, Base, get_db
from .graphql_schema import graphql_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
      # for 開発中のみDBを削除。普段はコメントアウト
      await conn.run_sync(Base.metadata.drop_all)
    
      # DBのテーブルを作成
      await conn.run_sync(Base.metadata.create_all)
      yield

app = FastAPI(lifespan=lifespan)

app.include_router(graphql_app, prefix="/graphql")


@app.post("/items/", response_model=schemas.ItemRead, status_code=201)
async def create_item_endpoint(item: schemas.ItemCreate, db: AsyncSession = Depends(get_db)):
    # ユニークチェックをすべきだが、ここでは省略
    return await crud.create_item(db=db, item=item)


@app.get("/items/", response_model=List[schemas.ItemRead])
async def read_items_endpoint(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    items = await crud.get_items(db=db, skip=skip, limit=limit)
    return items

@app.get("/items/{item_id}", response_model=schemas.ItemRead)
async def read_item_endpoint(item_id: int, db: AsyncSession = Depends(get_db)):
    db_item = await crud.get_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


@app.delete("/items/{item_id}", status_code=204)
async def delete_item_endpoint(item_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_item(db=db, item_id=item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return None


@app.put("/items/{item_id}", response_model=schemas.ItemRead)
async def update_item_endpoint(item_id: int, item_update: schemas.ItemCreate, db: AsyncSession = Depends(get_db)):
    db_updated_item = await crud.update_item(db=db, item_id=item_id, item_update=item_update)
    if db_updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_updated_item
