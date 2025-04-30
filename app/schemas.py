from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
import base64


# --- Base64URL encoded string type for better validation ---
class Base64UrlStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')
        try:
            # Attempt to decode to check if it's valid Base64URL
            base64.urlsafe_b64decode(v + '==') # Add padding for validation if needed
        except Exception:
            raise ValueError('invalid base64url encoding')
        return cls(v)

    def __repr__(self):
        return f'Base64UrlStr({super().__repr__()})'


# --- Item Schemas ---
class ItemBase(BaseModel):
  name: str
  description: Optional[str] = None
  price: float


class ItemCreate(ItemBase):
  pass


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., max_length=100)


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --- Credential Schemas ---
class CredentialBase(BaseModel):
    # Base64URL encoded string representation of credential_id
    credential_id_str: Base64UrlStr = Field(..., alias="credentialId")
    # Base64URL encoded string representation of public_key
    public_key_str: Base64UrlStr = Field(..., alias="publicKey")
    sign_count: int
    transports: Optional[List[str]] = None

    model_config = ConfigDict(populate_by_name=True) # Allow alias usage


class CredentialRead(CredentialBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int


# --- Passkey/WebAuthn Schemas ---
# Based on @simplewebauthn/typescript-types

class RegistrationResponseJSON(BaseModel):
    id: Base64UrlStr
    raw_id: Base64UrlStr = Field(..., alias="rawId")
    response: Dict[str, Any] # Contains attestationObject and clientDataJSON
    type: str
    client_extension_results: Dict[str, Any] = Field(..., alias="clientExtensionResults")
    authenticator_attachment: Optional[str] = Field(None, alias="authenticatorAttachment")

    model_config = ConfigDict(populate_by_name=True)


class AuthenticationResponseJSON(BaseModel):
    id: Base64UrlStr
    raw_id: Base64UrlStr = Field(..., alias="rawId")
    response: Dict[str, Any] # Contains authenticatorData, clientDataJSON, signature, userHandle
    type: str
    client_extension_results: Dict[str, Any] = Field(..., alias="clientExtensionResults")
    authenticator_attachment: Optional[str] = Field(None, alias="authenticatorAttachment")

    model_config = ConfigDict(populate_by_name=True)

# Schema for JWT token response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Schema for data within the JWT token
class TokenData(BaseModel):
    username: str | None = None
