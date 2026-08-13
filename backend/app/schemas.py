from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.wikilinks import UNLINKABLE_TITLE_REASON, is_linkable_title

Verdict = Literal["on_track", "diverging", "unclear"]


class Source(BaseModel):
    title: str | None = None
    url: str


class NodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(default="", max_length=100_000)
    tags: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        stripped = v.strip()
        if not is_linkable_title(stripped):
            raise ValueError(f"title {UNLINKABLE_TITLE_REASON}")
        return stripped

    @field_validator("tags")
    @classmethod
    def dedupe_tags(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for tag in v:
            stripped = tag.strip().lower()
            if stripped and stripped not in seen:
                seen.append(stripped)
        return seen


class NodeUpdate(BaseModel):
    """PATCH always applies every field the client includes in the request
    body (checked via model_fields_set) - the frontend always sends all three
    optional fields so "unset" (leave alone) and "null" (clear) never need to
    be distinguished in practice."""

    content_hash: str = Field(min_length=64, max_length=64)
    title: str | None = None
    body: str | None = None
    tags: list[str] | None = None

    # No linkability check here: notes are co-edited with Obsidian, so a title
    # already on disk may hold anything, and the frontend echoes it back on every
    # save. Only an actual rename is held to it, in notes.update_node.
    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("tags")
    @classmethod
    def dedupe_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        seen: list[str] = []
        for tag in v:
            stripped = tag.strip().lower()
            if stripped and stripped not in seen:
                seen.append(stripped)
        return seen

    @model_validator(mode="after")
    def require_a_change(self) -> "NodeUpdate":
        fields = self.model_fields_set - {"content_hash"}
        if not fields:
            raise ValueError("at least one of title, body, tags must be provided")
        return self


class LinkRef(BaseModel):
    target_raw: str
    alias: str | None
    node_id: str | None
    title: str | None


class NodeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    tags: list[str]
    excerpt: str
    updated_at: datetime
    latest_verdict: Verdict | None


class CheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    node_id: str
    verdict: Verdict
    reasoning: str
    sources: list[Source]
    created_at: datetime


class NodeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    path: str
    tags: list[str]
    body: str
    content_hash: str
    fm_error: str | None
    created_at: datetime
    updated_at: datetime
    links_out: list[LinkRef]
    backlinks: list[LinkRef]
    checks: list[CheckRead]
    # How many other notes a rename could not retarget (see notes.update_node).
    # Always 0 outside a PATCH response.
    link_rewrite_skipped: int = 0
    links_left_at_old_title: int = 0


class GraphNode(BaseModel):
    id: str
    title: str
    verdict: Verdict | None
    degree: int


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    unresolved: list[str]


class SyncReport(BaseModel):
    added: int
    updated: int
    removed: int
    errors: list[str]
