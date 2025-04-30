from sqlalchemy import String, Float, Integer, ForeignKey, LargeBinary, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from .database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    credentials: Mapped[List["Credential"]] = relationship("Credential", back_populates="user")


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False) # Base64URL encoded bytes
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transports: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True) # e.g. ["internal", "usb", "nfc", "ble"]

    user: Mapped["User"] = relationship("User", back_populates="credentials")
