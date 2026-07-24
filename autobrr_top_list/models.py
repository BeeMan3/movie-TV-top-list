from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"


class ContentItem(BaseModel):
    title: str = Field(..., min_length=1)
    type: ContentType
    average_rating: float | None = Field(default=None)


class SimpleContentItem(BaseModel):
    title: str = Field(..., min_length=1)


class DetailedOutput(BaseModel):
    last_updated: datetime = Field(default_factory=datetime.now)
    total_items: int
    items: list[ContentItem] = Field(default_factory=list)
