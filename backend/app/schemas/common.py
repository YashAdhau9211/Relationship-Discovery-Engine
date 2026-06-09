from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(examples=["entity_not_found"])
    message: str = Field(examples=["Entity was not found."])
    details: dict[str, Any] = Field(default_factory=dict)


class ApiError(BaseModel):
    error: ErrorDetail


class Explanation(BaseModel):
    summary: str
    algorithms: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
