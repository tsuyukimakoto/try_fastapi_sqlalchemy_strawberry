from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from .database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
