# ARCH-01 Validation: Minimal FastAPI + async SQLAlchemy (aiosqlite)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import event, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import asyncio
import random

# --- Database setup ---

class Base(DeclarativeBase):
    pass

class Counter(Base):
    __tablename__ = "counters"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[int] = mapped_column(default=0)

# WAL pragmas as specified in CLAUDE.md
async def set_wal_pragma(dbapi_conn, connection_record):
    """Set all required SQLite pragmas on each new connection."""
    await dbapi_conn.execute("PRAGMA journal_mode = WAL")
    await dbapi_conn.execute("PRAGMA busy_timeout = 5000")
    await dbapi_conn.execute("PRAGMA synchronous = NORMAL")
    await dbapi_conn.execute("PRAGMA foreign_keys = ON")
    await dbapi_conn.execute("PRAGMA mmap_size = 134217728")
    await dbapi_conn.execute("PRAGMA cache_size = -32000")
    await dbapi_conn.execute("PRAGMA wal_autocheckpoint = 1000")

engine = create_async_engine("sqlite+aiosqlite:///./arch01_test.db", echo=False)
event.listen(engine.sync_engine, "connect", lambda dbapi_conn, rec: print("[NOTE] DB connect event fired (sync_engine connect)"))

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# --- FastAPI ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialise a single counter row
    session = AsyncSessionLocal()
    try:
        from sqlalchemy import select
        existing = await session.execute(select(Counter).where(Counter.name == "test"))
        if not existing.scalar_one_or_none():
            session.add(Counter(name="test", value=0))
            await session.commit()
    finally:
        await session.close()
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/increment")
async def increment(amount: int = 1):
    """Increment the shared counter.

    Spends a short time in the DB to increase contention.
    """
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, update
        # read-modify-write on the same row -> high contention
        counter = await session.execute(select(Counter).where(Counter.name == "test"))
        counter = counter.scalar_one()
        await asyncio.sleep(random.uniform(0.01, 0.05))  # artificial delay
        counter.value += amount
        await session.commit()
    return {"new_value": counter.value}

@app.get("/value")
async def get_value():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Counter).where(Counter.name == "test"))
        return {"value": result.scalar_one().value}
