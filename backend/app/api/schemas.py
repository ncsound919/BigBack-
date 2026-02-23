from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class ItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
