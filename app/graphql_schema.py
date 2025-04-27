import strawberry
from strawberry.fastapi import BaseContext, GraphQLRouter
from strawberry.types import Info as _Info
from typing import List, Optional, AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db


Context = _Info['ContextData', None]

class ContextData(BaseContext):
  db: AsyncSession

  def __init__(self, db: AsyncSession):
    self.db = db


async def get_graphql_context(db: AsyncSession = Depends(get_db)) -> ContextData:
  return ContextData(db=db)


@strawberry.experimental.pydantic.type(model=schemas.ItemRead, all_fields=True)
class ItemType:
  pass


@strawberry.experimental.pydantic.input(model=schemas.ItemCreate, all_fields=True)
class ItemInput:
  pass


@strawberry.type
class Query:
  @strawberry.field
  async def items(self, info: Context, skip: int = 0, limit: int = 10) -> List[ItemType]:
    db = info.context.db
    items_db = await crud.get_items(db=db, skip=skip, limit=limit)
    
    #return [ItemType.from_pydantic(item) for item in items_db]
    # pydantic連携で、ORMインスタンスが自動的にItemTypeに変換される
    return items_db

  @strawberry.field
  async def item(self, info: Context, item_id: int) -> Optional[ItemType]:
    db = info.context.db
    item_db = await crud.get_item(db=db, item_id=item_id)
    if item_db is None:
      return None
    return item_db
  
  @strawberry.type
  class Mutation:
    @strawberry.mutation
    async def add_item(self, info: Context, item: ItemInput) -> ItemType:
      db = info.context.db
      item_create_schema = schemas.ItemCreate(**item.model_dump())
      created_item = await crud.create_item(db=db, item=item_create_schema)
      return created_item

    @strawberry.mutation
    async def update_item(self, info: Context, item_id: int, item: ItemInput) -> Optional[ItemType]:
      db = info.context.db
      return await crud.update_item(db=db, item_id=item_id, item_update=item)

    @strawberry.mutation
    async def delete_item(self, info: Context, item_id: int) -> bool:
      db = info.context.db
      deleted = await crud.delete_item(db=db, item_id=item_id)
      return deleted


schemas = strawberry.Schema(query=Query, mutation=Query.Mutation)

graphql_app = GraphQLRouter(
    schemas,
    context_getter=get_graphql_context,
    graphiql=True,  # GraphiQL UIを有効にする場合はコメントアウトを外す
)
