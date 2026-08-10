from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Thesis(Base):
    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    thesis_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    checks: Mapped[list["ThesisCheck"]] = relationship(
        back_populates="thesis",
        cascade="all, delete-orphan",
        order_by="ThesisCheck.created_at.desc()",
    )


class ThesisCheck(Base):
    __tablename__ = "thesis_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    thesis_id: Mapped[int] = mapped_column(ForeignKey("theses.id"))
    verdict: Mapped[str] = mapped_column(String(20))
    reasoning: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thesis: Mapped[Thesis] = relationship(back_populates="checks")
