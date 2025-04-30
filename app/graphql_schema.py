import strawberry
from strawberry.exceptions import StrawberryException # Import from strawberry.exceptions
from strawberry.fastapi import BaseContext, GraphQLRouter
from strawberry.types import Info as _Info
from typing import List, Optional, AsyncGenerator, Dict, Any
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import base64 # base64 を追加
import json # JSON スカラー用

from . import crud, models, schemas, auth # auth をインポート
from .database import get_db


# JSON スカラータイプを定義 (Strawberry はデフォルトで JSON をサポートしないため)
JSON = strawberry.scalar(
    Any, serialize=lambda v: v, parse_value=lambda v: v, description="Generic JSON scalar"
)


async def get_current_user_from_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[models.User]:
    """
    Extracts user from Authorization header token (if present).
    Returns None if no token or invalid token. Does not raise Exception.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            try:
                # Use a modified version or wrapper around get_current_user that doesn't raise HTTPException
                # For simplicity here, we'll call it directly and catch the exception.
                return await auth.get_current_user(token=token, db=db)
            except HTTPException:
                return None # Invalid token treated as no user
    return None


class ContextData(BaseContext):
    db: AsyncSession
    request: Request
    response: Response
    current_user: Optional[models.User]

    def __init__(self, db: AsyncSession, request: Request, response: Response, current_user: Optional[models.User]):
        # BaseContext doesn't take request/response in __init__
        super().__init__()
        self.db = db
        # Store request and response directly on the context if needed elsewhere
        self.request = request
        self.response = response
        self.current_user = current_user

# Update type hint for Info
Context = _Info[ContextData, None]


async def get_graphql_context(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_from_token) # トークンからユーザー取得
) -> ContextData:
    return ContextData(db=db, request=request, response=response, current_user=current_user)


# --- Strawberry Types ---

@strawberry.experimental.pydantic.type(model=schemas.UserRead, all_fields=True)
class UserType:
    pass

@strawberry.experimental.pydantic.type(model=schemas.Token, all_fields=True)
class TokenType:
    pass

@strawberry.experimental.pydantic.type(model=schemas.ItemRead, all_fields=True)
class ItemType:
  pass


@strawberry.experimental.pydantic.input(model=schemas.UserCreate, all_fields=True)
class UserInput:
    pass

@strawberry.experimental.pydantic.input(model=schemas.ItemCreate, all_fields=True)
class ItemInput:
  pass

# Input type for Passkey registration verification
@strawberry.input
class RegistrationVerificationInput:
    username: str
    registration_response_json: str # JSON string from frontend RegistrationResponseJSON
    challenge_key: str # Key used to store/retrieve challenge (e.g., from save_challenge)

# Input type for Passkey authentication verification
@strawberry.input
class AuthenticationVerificationInput:
    credential_id_b64: str # Base64URL encoded credential ID
    authentication_response_json: str # JSON string from frontend AuthenticationResponseJSON
    challenge_key: str # Key used to store/retrieve challenge


# --- Permissions ---
class IsAuthenticated(strawberry.permission.BasePermission):
    message = "User is not authenticated."

    # This method can also be async!
    def has_permission(self, source: Any, info: Context, **kwargs) -> bool:
        if info.context.current_user:
            return True
        return False




# --- Query ---
@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated]) # 保護されたクエリ
    async def me(self, info: Context) -> UserType:
        # IsAuthenticated でチェック済みなので current_user は存在するはず
        return UserType.from_pydantic(info.context.current_user)

    @strawberry.field
    async def generate_registration_options(
        self, info: Context, username: str, display_name: str
    ) -> JSON:
        db = info.context.db
        # ユーザーが存在するか確認、なければ作成
        user = await crud.get_user_by_username(db, username=username)
        if not user:
             # Pydantic モデルを使ってバリデーション
            try:
                user_create = schemas.UserCreate(username=username, display_name=display_name)
            except ValueError as e:
                raise StrawberryException(f"Invalid user data: {e}")
            user = await crud.create_user(db, user=user_create)
        elif user.display_name != display_name:
            # 既存ユーザーだが表示名が異なる場合はエラーにするか更新するか要検討
             raise StrawberryException(f"Username '{username}' already exists with a different display name.")

        existing_credentials = await crud.get_credentials_by_user(db, user.id)
        options = await auth.generate_registration_options(user, existing_credentials)

        # チャレンジを保存 (キーにはユーザー名と 'reg' タイプを使用)
        challenge_key = auth.generate_challenge_key(username, "reg")
        await auth.save_challenge(challenge_key, options["challenge"])

        # フロントエンドが使いやすいようにキー情報も返す
        return {"options": options, "challengeKey": challenge_key}

    @strawberry.field
    async def generate_authentication_options(
        self, info: Context, username: Optional[str] = None
    ) -> JSON:
        db = info.context.db
        # username なしの場合、Discoverable Credentials (Resident Key) を想定
        # user_handle はフロントエンド側で選択されるため、ここでは username の有無で判断
        try:
            options = await auth.generate_authentication_options(username=username, db=db)
        except HTTPException as e:
             # ユーザーが見つからない場合など
             raise StrawberryException(e.detail)

        # チャレンジを保存 (キーにはユーザー名または 'auth' タイプを使用)
        challenge_key = auth.generate_challenge_key(username or "discoverable", "auth")
        await auth.save_challenge(challenge_key, options["challenge"])

        return {"options": options, "challengeKey": challenge_key}


    # --- Item Queries (Protected) ---
    @strawberry.field(permission_classes=[IsAuthenticated])
    async def items(self, info: Context, skip: int = 0, limit: int = 10) -> List[ItemType]:
        db = info.context.db
        items_db = await crud.get_items(db=db, skip=skip, limit=limit)
        return [ItemType.from_pydantic(item) for item in items_db]

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def item(self, info: Context, item_id: int) -> Optional[ItemType]:
        db = info.context.db
        item_db = await crud.get_item(db=db, item_id=item_id)
        if item_db is None:
            return None
        return ItemType.from_pydantic(item_db)


# --- Mutation ---
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def register_user(self, info: Context, user_input: UserInput) -> UserType:
        db = info.context.db
        existing_user = await crud.get_user_by_username(db, username=user_input.username)
        if existing_user:
            raise StrawberryException(f"Username '{user_input.username}' is already taken.")
        user = await crud.create_user(db=db, user=user_input)
        return UserType.from_pydantic(user)

    @strawberry.mutation
    async def verify_registration(self, info: Context, verification_input: RegistrationVerificationInput) -> bool:
        db = info.context.db
        username = verification_input.username
        challenge_key = verification_input.challenge_key

        user = await crud.get_user_by_username(db, username=username)
        if not user:
            raise StrawberryException(f"User '{username}' not found.")

        # 保存したチャレンジを取得
        challenge_b64 = await auth.get_challenge(challenge_key)
        if not challenge_b64:
            raise StrawberryException("Registration challenge expired or not found. Please try registering again.")

        # フロントエンドからの JSON 文字列をパース
        try:
            reg_response_dict = json.loads(verification_input.registration_response_json)
            registration_response = schemas.RegistrationResponseJSON(**reg_response_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise StrawberryException(f"Invalid registration response format: {e}")

        try:
            attested_credential_data = await auth.verify_registration(
                user=user,
                registration_response=registration_response,
                expected_challenge_b64=challenge_b64,
            )

            # 新しいクレデンシャルをDBに保存
            await crud.add_credential_to_user(
                db=db,
                user=user,
                credential_id_b64=registration_response.id, # registration_response.id is already Base64URL string
                public_key_b64=base64.urlsafe_b64encode(attested_credential_data.credential_public_key).rstrip(b'=').decode('utf-8'),
                sign_count=attested_credential_data.sign_count,
                transports=registration_response.response.get("transports") # Optional transports
            )
            return True
        except HTTPException as e:
             raise StrawberryException(e.detail)
        except Exception as e:
             # Log unexpected errors
             print(f"Unexpected error verifying registration: {e}") # Replace with proper logging
             raise StrawberryException("An unexpected error occurred during registration verification.")


    @strawberry.mutation
    async def verify_authentication(self, info: Context, verification_input: AuthenticationVerificationInput) -> TokenType:
        db = info.context.db
        credential_id_b64 = verification_input.credential_id_b64
        challenge_key = verification_input.challenge_key

        # 保存したチャレンジを取得
        challenge_b64 = await auth.get_challenge(challenge_key)
        if not challenge_b64:
            raise StrawberryException("Authentication challenge expired or not found. Please try logging in again.")

        # フロントエンドからの JSON 文字列をパース
        try:
            auth_response_dict = json.loads(verification_input.authentication_response_json)
            authentication_response = schemas.AuthenticationResponseJSON(**auth_response_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise StrawberryException(f"Invalid authentication response format: {e}")

        try:
            verified_credential = await auth.verify_authentication(
                credential_id_b64=credential_id_b64,
                auth_response=authentication_response,
                expected_challenge_b64=challenge_b64,
                db=db
            )

            # 認証成功、JWT を生成
            access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = auth.create_access_token(
                data={"sub": verified_credential.user.username}, expires_delta=access_token_expires
            )
            return TokenType(access_token=access_token, token_type="bearer")

        except HTTPException as e:
            raise StrawberryException(e.detail)
        except Exception as e:
             print(f"Unexpected error verifying authentication: {e}") # Replace with proper logging
             raise StrawberryException("An unexpected error occurred during authentication verification.")


    # --- Item Mutations (Protected) ---
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def add_item(self, info: Context, item: ItemInput) -> ItemType:
        db = info.context.db
        # item_create_schema = schemas.ItemCreate(**item.__dict__) # This might not work well with Strawberry inputs
        item_create_schema = schemas.ItemCreate(name=item.name, description=item.description, price=item.price)
        created_item = await crud.create_item(db=db, item=item_create_schema)
        return ItemType.from_pydantic(created_item)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def update_item(self, info: Context, item_id: int, item: ItemInput) -> Optional[ItemType]:
        db = info.context.db
        # item_update_schema = schemas.ItemCreate(**item.__dict__)
        item_update_schema = schemas.ItemCreate(name=item.name, description=item.description, price=item.price)
        updated_item = await crud.update_item(db=db, item_id=item_id, item_update=item_update_schema)
        if updated_item is None:
             return None
        return ItemType.from_pydantic(updated_item)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def delete_item(self, info: Context, item_id: int) -> bool:
        db = info.context.db
        deleted = await crud.delete_item(db=db, item_id=item_id)
        return deleted



# Schema を Query と Mutation で初期化
schema = strawberry.Schema(query=Query, mutation=Mutation) # Mutation クラスを渡す

# GraphQL ルーターを更新されたコンテキストゲッターで設定
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context, # 更新された context_getter を使用
    graphiql=True,
)
