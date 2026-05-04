from datetime import datetime

from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Соглашение об именовании индексов (важно для Alembic)
# ix = index, uq = unique, ck = check, fk = foreign key, pk = primary key
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Главный класс, от которого наследуются все таблицы.
    Включает автоматическое именование констрейнтов.
    """

    metadata = MetaData(naming_convention=convention)


class TimestampMixin:
    """
    Миксин для добавления полей временных меток `created_at` и `updated_at`
    к моделям SQLAlchemy.

    Эти поля автоматически управляются базой данных на уровне сервера (в UTC).
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        comment="Время создания записи (UTC).",
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Время последнего обновления записи (UTC).",
    )
