import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.frontend.core.database import Base


class Survey(Base):
    __tablename__ = "surveys"
    __table_args__ = {"schema": "site"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    questions: Mapped[list["SurveyQuestion"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan", order_by="SurveyQuestion.order",
    )
    sends: Mapped[list["SurveySend"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan",
    )


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    __table_args__ = {"schema": "site"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("site.surveys.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    choices_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    survey: Mapped["Survey"] = relationship(back_populates="questions")


class SurveySend(Base):
    __tablename__ = "survey_sends"
    __table_args__ = {"schema": "site"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("site.surveys.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("site.auth_users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["Survey"] = relationship(back_populates="sends")
    response: Mapped["SurveyResponse | None"] = relationship(back_populates="send", uselist=False)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    __table_args__ = {"schema": "site"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    send_id: Mapped[int] = mapped_column(ForeignKey("site.survey_sends.id"), unique=True, nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    send: Mapped["SurveySend"] = relationship(back_populates="response")
