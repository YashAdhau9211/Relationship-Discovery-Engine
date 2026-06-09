from typing import Any

from pydantic import BaseModel, Field


class EntitySummary(BaseModel):
    id: str = Field(examples=["person:alice-chen"])
    label: str = Field(examples=["Person"])
    display_name: str = Field(examples=["Alice Chen"])
    properties: dict[str, Any] = Field(default_factory=dict)


class EntityDetail(EntitySummary):
    aliases: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class EntitySearchResponse(BaseModel):
    query: str
    count: int
    results: list[EntitySummary]
