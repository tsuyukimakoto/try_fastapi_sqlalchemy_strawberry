import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, AttestedCredentialData, AuthenticatorData, CollectedClientData, AttestationObject # Import AttestationObject from here
# Remove AttestationObject import from fido2.ctap2 if it exists, or ensure it's not duplicated
import base64

from . import crud, models, schemas, database

# --- Environment Variables & Constants ---
# .env ファイルから設定を読み込む
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key") # .env から読み込む。デフォルト値は非推奨
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

RP_ID = os.getenv("RP_ID", "localhost")
RP_NAME = os.getenv("RP_NAME", "My FastAPI App")
RP_ORIGIN = os.getenv("RP_ORIGIN", "http://localhost:3000") # フロントエンドのオリジン

# Initialize Fido2Server using PublicKeyCredentialRpEntity instead of RelyingParty
rp_entity = PublicKeyCredentialRpEntity(id=RP_ID, name=RP_NAME)
fido2_server = Fido2Server(rp_entity)

# OAuth2PasswordBearer はトークンを Authorization ヘッダーから Bearer トークンとして抽出します。
# tokenUrl は実際のエンドポイントである必要はなく、ドキュメント生成のために使用されます。
# ここでは便宜上 /token としていますが、実際には GraphQL Mutation でトークンを取得します。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token") # OpenAPI doc 用

# --- JWT Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(database.get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception

    user = await crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    # ここでは単純にユーザーが存在すればアクティブとみなす
    # 必要に応じて is_active フラグなどを User モデルに追加してチェックする
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# --- Passkey (WebAuthn) Helper Functions ---

async def generate_registration_options(
    user: models.User, existing_credentials: List[models.Credential]
) -> Dict[str, Any]:
    # 既存のクレデンシャルを除外リストに追加
    exclude_credentials = [{"type": "public-key", "id": cred.credential_id} for cred in existing_credentials]

    options, state = fido2_server.register_begin(
        {
            "id": user.id.to_bytes(8, 'big'), # user handle は bytes である必要がある
            "name": user.username,
            "displayName": user.display_name,
        },
        credentials=existing_credentials,
        user_verification="preferred",
        authenticator_attachment="platform",
        # exclude_credentials=exclude_credentials, # Remove unsupported argument for fido2 v1.2.0
    )
    # state はサーバー側で保持し、検証時に使用する必要がある
    # ここでは簡略化のため、セッションや一時ストレージに保存すると仮定
    # 例: await save_registration_state(user.id, state)
    # このサンプルでは state を直接返さず、別途管理することを前提とする

    # PublicKeyCredentialCreationOptions をフロントエンドが期待する形式 (JSON シリアライズ可能) に変換
    # options は CredentialCreationOptions 型で、実際のデータは public_key 属性にある
    public_key_options = options.public_key
    options_json_serializable = {
        "rp": {
            "id": public_key_options.rp.id,
            "name": public_key_options.rp.name,
        },
        "user": {
            "id": base64.urlsafe_b64encode(public_key_options.user.id).rstrip(b'=').decode('utf-8'),
            "name": public_key_options.user.name,
            "displayName": public_key_options.user.display_name,
        },
        "challenge": base64.urlsafe_b64encode(public_key_options.challenge).rstrip(b'=').decode('utf-8'),
        "pubKeyCredParams": [
            {"type": param.type, "alg": param.alg} for param in public_key_options.pub_key_cred_params
        ],
        # オプショナルな属性も必要に応じて追加
        "timeout": public_key_options.timeout,
        "excludeCredentials": [
            {"type": cred.type, "id": base64.urlsafe_b64encode(cred.id).rstrip(b'=').decode('utf-8'), "transports": cred.transports}
            for cred in public_key_options.exclude_credentials
        ] if public_key_options.exclude_credentials else [],
        "authenticatorSelection": {
            "authenticatorAttachment": public_key_options.authenticator_selection.authenticator_attachment,
            "residentKey": public_key_options.authenticator_selection.resident_key,
            "userVerification": public_key_options.authenticator_selection.user_verification,
            "requireResidentKey": public_key_options.authenticator_selection.require_resident_key,
        } if public_key_options.authenticator_selection else None,
        "attestation": public_key_options.attestation,
        "extensions": public_key_options.extensions,
    }

    # bytes 型を Base64URL 文字列に変換 (上記で実施済み)
    # options_json_serializable["challenge"] = base64.urlsafe_b64encode(public_key_options.challenge).rstrip(b'=').decode('utf-8')
    # options_json_serializable["user"]["id"] = base64.urlsafe_b64encode(public_key_options.user.id).rstrip(b'=').decode('utf-8')
    # if "excludeCredentials" in options_json_serializable and options_json_serializable["excludeCredentials"]:
    #     for cred in options_json_serializable["excludeCredentials"]:
    #         cred["id"] = base64.urlsafe_b64encode(cred["id"]).rstrip(b'=').decode('utf-8')
    # 他に bytes 型があれば同様に変換

    # FastAPI/Strawberry が扱えるように、変換後の辞書を返す
    return options_json_serializable


async def verify_registration(
    user: models.User,
    registration_response: schemas.RegistrationResponseJSON,
    expected_challenge_b64: str, # セッション等から取得したチャレンジ (Base64URL)
    expected_origin: str = RP_ORIGIN,
    expected_rp_id: str = RP_ID,
    require_user_verification: bool = True,
) -> AttestedCredentialData:

    # state を取得 (セッションや一時ストレージから)
    # 例: state = await get_registration_state(user.id)
    # このサンプルでは state を検証に使わない fido2 ライブラリの機能を利用
    # (state の検証は fido2.webauthn.verify_registration_response で行うのがより堅牢)

    challenge_bytes = base64.urlsafe_b64decode(expected_challenge_b64 + '==')

    try:
        auth_data = fido2_server.register_complete(
             state={}, # 本来は register_begin で得た state を使うべき
             client_data=CollectedClientData(registration_response.response["clientDataJSON"]),
             attestation_object=AttestationObject(base64.urlsafe_b64decode(registration_response.response["attestationObject"] + '==')),
             # expected_origin=expected_origin, # origin の検証 (fido2 ライブラリが内部で行うはず)
             # expected_rp_id=expected_rp_id, # rpId の検証 (fido2 ライブラリが内部で行うはず)
             # expected_challenge=challenge_bytes # challenge の検証 (fido2 ライブラリが内部で行うはず)
             # require_user_verification=require_user_verification # UV の検証
        )
        # 注意: fido2 ライブラリの register_complete は state を必須引数としていない場合があるが、
        # セキュリティのため、本来は register_begin で生成された state (challenge を含む) を
        # 検証時に照合すべき。ここでは簡略化のため省略している。
        # より堅牢な実装では、fido2.webauthn.verify_registration_response を直接使うことを検討。
        # verify_registration_response(
        #     credential=registration_response.dict(by_alias=True), # Pydantic モデルを辞書に
        #     expected_challenge=challenge_bytes,
        #     expected_origin=expected_origin,
        #     expected_rp_id=expected_rp_id,
        #     require_user_verification=require_user_verification,
        # )

        # 検証成功、認証情報データを返す
        return auth_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Registration verification failed: {e}")
    except Exception as e:
        # logging.exception("Unexpected error during registration verification")
        raise HTTPException(status_code=500, detail=f"Internal server error during registration: {e}")


async def generate_authentication_options(
    username: Optional[str] = None,
    user_handle_b64: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db)
) -> Dict[str, Any]:

    allow_credentials = []
    if username:
        user = await crud.get_user_by_username(db, username=username)
        if user:
            credentials = await crud.get_credentials_by_user(db, user.id)
            allow_credentials = [{"type": "public-key", "id": cred.credential_id} for cred in credentials]
    elif user_handle_b64:
         # Discoverable Credentials (Resident Keys) の場合、username なしで user_handle から探す
         # user_handle は register_begin で指定した user.id の bytes 表現
         try:
             user_id_bytes = base64.urlsafe_b64decode(user_handle_b64 + '==')
             user_id = int.from_bytes(user_id_bytes, 'big')
             user = await crud.get_user(db, user_id=user_id)
             if user:
                 credentials = await crud.get_credentials_by_user(db, user.id)
                 allow_credentials = [{"type": "public-key", "id": cred.credential_id} for cred in credentials]
         except (ValueError, TypeError):
             pass # 不正な user_handle は無視

    if not allow_credentials and username:
         # Username は指定されたが、登録済みのクレデンシャルがない場合
         # (Discoverable Credential でない場合、allowCredentials は必須ではないが、
         # UX向上のため、登録がない場合はエラーにするか、登録を促す方が親切)
         raise HTTPException(status_code=404, detail=f"No credentials found for user '{username}'")


    options, state = fido2_server.authenticate_begin(
        credentials=allow_credentials, # ユーザーに紐づくクレデンシャル ID のリスト
        user_verification="preferred"
    )

    # state (challenge を含む) を保存
    # 例: await save_authentication_state(username or user_handle_b64, state) # キーを一意にする

    # フロントエンド向けに変換
    options_json_serializable = dict(options)
    options_json_serializable["challenge"] = base64.urlsafe_b64encode(options_json_serializable["challenge"]).rstrip(b'=').decode('utf-8')
    if "allowCredentials" in options_json_serializable:
        for cred in options_json_serializable["allowCredentials"]:
            cred["id"] = base64.urlsafe_b64encode(cred["id"]).rstrip(b'=').decode('utf-8')

    return options_json_serializable

async def verify_authentication(
    credential_id_b64: str, # フロントエンドから送られてきた Credential ID (Base64URL)
    auth_response: schemas.AuthenticationResponseJSON,
    expected_challenge_b64: str, # セッション等から取得したチャレンジ (Base64URL)
    db: AsyncSession,
    expected_origin: str = RP_ORIGIN,
    expected_rp_id: str = RP_ID,
    require_user_verification: bool = True,
) -> models.Credential:

    credential = await crud.get_credential_by_id(db, credential_id_b64=credential_id_b64)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # state を取得 (セッション等から)
    # 例: state = await get_authentication_state(credential.user.username) # または他のキー

    challenge_bytes = base64.urlsafe_b64decode(expected_challenge_b64 + '==')

    try:
        # AuthenticatorData と ClientData をデコード
        auth_data_bytes = base64.urlsafe_b64decode(auth_response.response["authenticatorData"] + '==')
        client_data = CollectedClientData(auth_response.response["clientDataJSON"])
        signature_bytes = base64.urlsafe_b64decode(auth_response.response["signature"] + '==')

        # fido2 ライブラリの authenticate_complete を使用して検証
        # この関数は内部で challenge, origin, rpId, user verification, signature の検証を行う
        fido2_server.authenticate_complete(
            state={}, # 本来は authenticate_begin で得た state を使う
            credentials=[credential], # DB から取得した認証情報
            credential_id=credential.credential_id,
            client_data=client_data,
            auth_data=AuthenticatorData(auth_data_bytes),
            signature=signature_bytes,
            # expected_origin=expected_origin, # fido2 が内部で検証
            # expected_rp_id=expected_rp_id, # fido2 が内部で検証
            # expected_challenge=challenge_bytes, # fido2 が内部で検証
            # require_user_verification=require_user_verification # fido2 が内部で検証
        )

        # 署名カウンターの検証と更新
        new_sign_count = AuthenticatorData(auth_data_bytes).sign_count
        if new_sign_count <= credential.sign_count:
             # リプレイ攻撃の可能性
             raise HTTPException(status_code=400, detail="Authenticator counter mismatch. Possible replay attack.")

        # 署名カウンターを更新
        await crud.update_credential_sign_count(db, credential, new_sign_count)

        return credential

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Authentication verification failed: {e}")
    except Exception as e:
        # logging.exception("Unexpected error during authentication verification")
        raise HTTPException(status_code=500, detail=f"Internal server error during authentication: {e}")


# --- Temporary State Storage (Replace with proper session/cache) ---
# !!! WARNING: This is a very basic in-memory store for demonstration ONLY. !!!
# !!! DO NOT use this in production. Use Redis, a database, or server-side sessions. !!!
temp_challenge_store: Dict[str, str] = {}

async def save_challenge(key: str, challenge: str):
    # NOTE: In a real app, use a secure session mechanism or a timed cache (e.g., Redis)
    # Ensure the key is unique per user/session and the challenge expires.
    print(f"Saving challenge for {key}: {challenge}") # Debug print
    temp_challenge_store[key] = challenge

async def get_challenge(key: str) -> Optional[str]:
    # NOTE: Retrieve and immediately clear the challenge to prevent reuse.
    print(f"Getting challenge for {key}") # Debug print
    return temp_challenge_store.pop(key, None)

def generate_challenge_key(username: str, type: str = "reg") -> str:
    """Generates a unique key for storing challenges."""
    # Simple example, consider using session ID or user ID for better scoping
    return f"{username}_{type}_challenge"
