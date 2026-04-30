from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class ScenarioNode(Base):
    __tablename__ = "scenario_nodes"
    __table_args__ = (UniqueConstraint("quest_key", "node_key", name="uq_scenario_nodes_quest_node_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quest_key: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("scenario_master.quest_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alerts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    node_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
