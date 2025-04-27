from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import AsyncGenerator


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 非同期エンジン
engine = create_async_engine(
   SQLALCHEMY_DATABASE_URL,
  #  connection_args={"check_same_thread": False},
   echo=True
)


# 非同期セッションファクトリ
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
  pass


# FastAPIのDIで使用するDBセッションを取得するための関数
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
