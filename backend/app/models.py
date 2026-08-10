from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    path: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    title_norm: Mapped[str] = mapped_column(String(300), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="note")
    ticker: Mapped[str | None] = mapped_column(String(16), index=True, default=None)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    body: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    mtime_ns: Mapped[int] = mapped_column(BigInteger)
    size: Mapped[int] = mapped_column(Integer)
    fm_error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    links_out: Mapped[list["NodeLink"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    checks: Mapped[list["Check"]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="Check.created_at.desc()",
    )


class NodeLink(Base):
    __tablename__ = "node_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    target_raw: Mapped[str] = mapped_column(String(300))
    target_norm: Mapped[str] = mapped_column(String(300), index=True)
    alias: Mapped[str | None] = mapped_column(String(300), default=None)

    source: Mapped[Node] = relationship(back_populates="links_out")


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(500), unique=True)
    verdict: Mapped[str] = mapped_column(String(20))
    reasoning: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    model: Mapped[str | None] = mapped_column(String(120), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    node: Mapped[Node] = relationship(back_populates="checks")
