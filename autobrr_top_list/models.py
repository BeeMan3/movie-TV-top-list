from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class ContentType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"


class ContentItem(BaseModel):
    title: str = Field(..., min_length=1)
    type: ContentType
    average_rating: Optional[float] = Field(default=None)


class SimpleContentItem(BaseModel):
    title: str = Field(..., min_length=1)


class DetailedOutput(BaseModel):
    last_updated: datetime = Field(default_factory=datetime.now)
    total_items: int
    items: List[ContentItem] = Field(default_factory=list)


class AggregateRating(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    ratingValue: Optional[Union[str, float]] = None

    def rating_value_as_float(self) -> Optional[float]:
        if self.ratingValue is None:
            return None
        try:
            return float(self.ratingValue)
        except (TypeError, ValueError):
            return None


class LdItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    name: Optional[str] = None
    alternateName: Optional[str] = None
    headline: Optional[str] = None
    aggregateRating: Optional[AggregateRating] = None


class LdListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    position: Optional[int] = None
    item: Optional[Union[LdItem, dict]] = None


class ItemListLD(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    itemListElement: List[Union[LdListItem, LdItem, dict]] = Field(default_factory=list)
