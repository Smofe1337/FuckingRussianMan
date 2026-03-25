# database — sqlalchemy orm with both sync and async sessions
# sync session for llm/rag that run in thread executors
# async session for aiogram/telethon handlers that live in the event loop

import logging
from typing import List

from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from src.storage.models import Base, LearnedMessage

log = logging.getLogger(__name__)


class Database:
    # two engines same file — sync for executor-bound code async for everything else

    def __init__(self, db_path: str) -> None:
        # sync engine — used by llm and rag running in thread pool
        self._engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
        )
        # async engine — used by aiogram and telethon handlers
        self._async_engine = create_async_engine(
            f'sqlite+aiosqlite:///{db_path}',
            connect_args={'check_same_thread': False},
        )
        self._async_session = async_sessionmaker(
            self._async_engine, expire_on_commit=False
        )
        # create tables via sync engine — simpler at startup
        Base.metadata.create_all(self._engine)

    # sync — for executor-bound code (llm rag)

    def _session(self) -> Session:
        return Session(self._engine)

    def get_transcripts(self) -> List[str]:
        # all texts random order — rag uses this to build the index
        with self._session() as s:
            rows = s.scalars(
                select(LearnedMessage.text)
                .where(func.length(LearnedMessage.text) > 15)
                .order_by(func.random())
            ).all()
        return list(rows)

    def get_learned(self, limit: int = 80) -> List[str]:
        # most recent messages — fallback when rag has nothing useful
        with self._session() as s:
            rows = s.scalars(
                select(LearnedMessage.text)
                .order_by(LearnedMessage.created_at.desc())
                .limit(limit)
            ).all()
        return list(rows)

    # async — for aiogram and telethon handlers

    async def save_learned(self, text: str, source: str = 'channel') -> None:
        # non-blocking insert — called from async handlers
        async with self._async_session() as s:
            s.add(LearnedMessage(text=text, source=source))
            await s.commit()

    async def stats(self) -> dict:
        # total count and source breakdown — shown in admin panel
        async with self._async_session() as s:
            total = await s.scalar(select(func.count()).select_from(LearnedMessage))
            result = await s.execute(
                select(LearnedMessage.source, func.count())
                .group_by(LearnedMessage.source)
            )
            by_source = dict(result.all())
        return {'total': total or 0, 'by_source': by_source}
