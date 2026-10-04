from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.proxy import via_proxy


class Base(DeclarativeBase):
    pass


# pre_ping replaces connections the Supabase pooler dropped while the app was idle.
engine = create_async_engine(
    via_proxy(settings.DATABASE_URL, settings.OUTBOUND_PROXY), pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
