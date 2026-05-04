from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID  # Используем JSONB вместо JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.database.postgres.models.base import Base, TimestampMixin


class ScenarioMaster(Base, TimestampMixin):
    """
    Таблица A: Глобальные настройки сценария (квеста).
    """

    __tablename__ = "scenario_master"

    quest_key: Mapped[str] = mapped_column(
        String(50), primary_key=True, comment="Уникальный ID квеста (напр. awakening_rift)."
    )
    start_node_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="ID начальной точки.")

    init_sync: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="(Импорт): Список команд для наполнения «песочницы» при старте квеста."
    )
    export_sync: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="(Экспорт): Список команд для возврата данных в реальный мир при завершении квеста.",
    )

    status_bar_fields: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="JSON-список полей для статус-бара."
    )
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Дополнительные настройки.")


class ScenarioNode(Base):
    """
    Таблица B: Контентная база. Каждая запись — это отдельная сцена.
    """

    __tablename__ = "scenario_nodes"

    # Добавляем уникальное ограничение для пары (quest_key, node_key)
    __table_args__ = (UniqueConstraint("quest_key", "node_key", name="uq_quest_node_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_key: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Уникальный ID шага внутри квеста."
    )
    quest_key: Mapped[str] = mapped_column(
        String(50), ForeignKey("scenario_master.quest_key", ondelete="CASCADE"), comment="Привязка к мастеру."
    )

    text_content: Mapped[str] = mapped_column(
        String, nullable=False, comment="Художественный текст с поддержкой плейсхолдеров."
    )

    # Используем JSONB для поддержки оператора contains (@>)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="Теги для группировки нод (Pools).")

    selection_requirements: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Фильтр на вход (Smart Selection)."
    )
    actions_logic: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Логика кнопок, математика изменений и переходы (Edges)."
    )


class CharacterScenarioState(Base, TimestampMixin):
    """
    Таблица C: Таблица резервного копирования ("Сейв").
    Хранит полный снимок сессии для восстановления.
    """

    __tablename__ = "character_scenario_state"

    __table_args__ = (UniqueConstraint("char_id", name="uq_char_scenario_state_char_id"),)

    char_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True, comment="ID персонажа."
    )
    quest_key: Mapped[str] = mapped_column(
        String(50), ForeignKey("scenario_master.quest_key"), primary_key=True, comment="ID текущего квеста."
    )

    current_node_key: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="ID текущей сцены (где игрок остановился)."
    )
    context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="Полный дамп переменных квеста (статы, флаги, токены)."
    )

    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="ID сессии (для валидации актуальности)."
    )
