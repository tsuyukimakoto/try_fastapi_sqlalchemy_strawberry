from pydantic import BaseModel, ConfigDict
from typing import Optional


class ItemBase(BaseModel):
  name: str
  description: Optional[str] = None
  price: float


class ItemCreate(ItemBase):
  pass


class ItemRead(ItemBase):
  model_config = ConfigDict(from_attributes=True)
  id: int
