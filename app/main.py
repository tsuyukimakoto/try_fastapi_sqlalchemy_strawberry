from fastapi import FastAPI # Remove Depends, HTTPException
# Remove typing imports if no longer needed by REST endpoints
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import os # Add os
from dotenv import load_dotenv # Add dotenv

# Load .env file early
load_dotenv()

# Remove unused imports if REST endpoints are gone
# from . import crud, models, schemas, database
from .database import engine, Base # Remove get_db if only used by REST endpoints
from .graphql_schema import graphql_app
from fastapi.middleware.cors import CORSMiddleware # Add CORS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # .env から DB リセット設定を読み込む
    reset_db = os.getenv("RESET_DB_ON_STARTUP", "False").lower() == "true"

    async with engine.begin() as conn:
      if reset_db:
          print("RESET_DB_ON_STARTUP is True. Dropping and recreating tables...")
          # すべてのテーブルを削除 (User, Credential テーブルも含む)
          await conn.run_sync(Base.metadata.drop_all)
      else:
          print("RESET_DB_ON_STARTUP is False. Skipping drop_all.")

      # DBのテーブルを作成 (存在しないテーブルのみ作成される)
      await conn.run_sync(Base.metadata.create_all)
      yield
    # Shutdown イベントがあればここに記述

app = FastAPI(lifespan=lifespan)

# CORS 設定 (一時的にすべて許可してデバッグ)
origins = ["*"] # Allow all origins for debugging

# CORS ミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Use the wildcard origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"], # Explicitly add OPTIONS
    allow_headers=["*"],
)

app.include_router(graphql_app, prefix="/graphql")

# Item 用 REST API エンドポイントは削除
