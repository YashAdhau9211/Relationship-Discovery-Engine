from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.entities import EntitySummary

SocialDirection = Literal["incoming", "outgoing", "undirected"]


class SocialConnection(BaseModel):
    entity: EntitySummary
    relationship_type: Literal["FOLLOWS", "FRIENDS_WITH"]
    direction: SocialDirection
    weight: float | None = None
    platform: str | None = None
    timestamp: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class MutualConnectionResponse(BaseModel):
    source_id: str
    target_id: str
    count: int
    mutuals: list[SocialConnection]


class SocialProfileResponse(BaseModel):
    entity_id: str
    follower_count: int
    following_count: int
    friend_count: int
    mutual_count: int
    follow_ratio: float | None
    platform_distribution: dict[str, int] = Field(default_factory=dict)
    top_followers: list[SocialConnection] = Field(default_factory=list)
    top_following: list[SocialConnection] = Field(default_factory=list)
    friends: list[SocialConnection] = Field(default_factory=list)


class SocialConnectionsResponse(BaseModel):
    entity_id: str
    relationship_type: Literal["FOLLOWS", "FRIENDS_WITH"]
    direction: SocialDirection
    count: int
    results: list[SocialConnection]
