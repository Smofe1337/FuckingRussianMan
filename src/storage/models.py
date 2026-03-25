# orm models — single table for now but easy to extend
# sqlalchemy declarative base keeps it clean

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LearnedMessage(Base):
    __tablename__ = 'learned_messages'

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    text:       Mapped[str]      = mapped_column(Text, nullable=False)
    source:     Mapped[str]      = mapped_column(String(64), default='channel')
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
