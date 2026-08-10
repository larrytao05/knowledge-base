from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Verdict = Literal["on_track", "diverging", "unclear"]


class ThesisCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    thesis_text: str = Field(min_length=1, max_length=5000)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()


class ThesisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticker: str
    thesis_text: str
    created_at: datetime


class Source(BaseModel):
    title: str | None = None
    url: str


class ThesisCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    thesis_id: int
    verdict: Verdict
    reasoning: str
    sources: list[Source]
    created_at: datetime


class ThesisDetail(ThesisRead):
    checks: list[ThesisCheckRead] = []
