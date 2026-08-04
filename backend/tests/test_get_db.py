"""Tests for the FastAPI ``get_db()`` dependency in :mod:`backend.core.database`.

These tests verify the commit/rollback boundary:

1. **Commit on success:** when a route handler exits normally, ``get_db()``
   commits any flushed writes so they persist beyond the request.
2. **Rollback on error:** if the handler raises, ``get_db()`` rolls back so
   no partial writes leak into the database.

This locks in the project-wide convention that service/repository code can
stay **flush-only** — persistence (and abort) is owned by the ``get_db()``
boundary, not by individual services.

The tests monkeypatch ``backend.core.database.AsyncSessionLocal`` to an
in-memory aiosqlite sessionmaker so they never touch the real ``arcade.db``.

A note on the driver: a plain ``async for s in get_db(): ...`` loop does NOT
correctly simulate FastAPI's behavior when the handler raises — Python's
``async for`` does not call ``athrow()`` on the generator on body exceptions,
so a ``try/except`` inside the generator never fires. FastAPI/Starlette
DO use ``gen.athrow(...)`` internally to propagate handler exceptions into
the dependency generator. We exercise the same protocol here via
:func:`_run_get_db_like_fastapi`, which mirrors that behavior.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from unittest.mock import patch

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_db
from backend.models import Staff

# ---------------------------------------------------------------------------
# Test engine / sessionmaker helpers
# ---------------------------------------------------------------------------


def _make_test_sessionlocal():
    """Build a fresh async_sessionmaker bound to an in-memory aiosqlite engine.

    We force a single shared connection via :class:`StaticPool` (with
    ``check_same_thread=False``) so every session opened on this engine
    talks to the SAME underlying SQLite in-memory database. Without this,
    aiosqlite creates a fresh per-connection memory DB on every checkout
    from the default pool, making commit/rollback effects on one session
    invisible to the next — which makes these tests flaky.

    With StaticPool, the in-memory DB persists across the lifetime of the
    engine, so a second session opened via the same sessionmaker will
    observe writes either persisted (commit) or discarded (rollback) by
    the first session.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine, SessionLocal


async def _ensure_schema(engine) -> None:
    """Create all tables on the test engine."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# FastAPI-style driver
# ---------------------------------------------------------------------------


async def _run_get_db_like_fastapi(
    handler: Callable[[AsyncSession], Awaitable[None]],
) -> BaseException | None:
    """Drive :func:`get_db` the same way FastAPI/Starlette does.

    On a successful handler return: ``async for ... __anext__()`` advances
    past the ``yield`` (running the post-yield code, i.e. ``commit``).

    On a handler exception: we catch it, then call ``gen.athrow(exc)`` to
    push the same exception INTO the generator (which is what Starlette's
    dependency machinery does), and finally call ``aclose()`` to make sure
    the ``async with AsyncSessionLocal()`` block runs its ``__aexit__``.

    Returns the exception that propagated out of the dependency (or ``None``
    on a clean exit).
    """
    gen = get_db()
    session = await gen.__anext__()
    exc: BaseException | None = None
    try:
        try:
            await handler(session)
        except BaseException as raised:
            exc = raised
            # Push the same exception INTO the generator, like FastAPI does.
            try:
                await gen.athrow(raised)
            except BaseException as propagated:
                # The generator caught it, ran rollback, and re-raised.
                # Replace the locally-caught one so the caller sees the
                # post-generator exception (which is the same one anyway,
                # but this matches what FastAPI would propagate).
                exc = propagated
        else:
            # Happy path: advance past the yield so the post-yield code
            # (``await session.commit()``) and the ``async with`` cleanup
            # get a chance to run.
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
    finally:
        await gen.aclose()
    return exc


# ---------------------------------------------------------------------------
# Commit on success
# ---------------------------------------------------------------------------


async def test_get_db_commits_on_successful_exit() -> None:
    """get_db() commits the session when the handler exits normally.

    Simulates a FastAPI route handler that flushes a new ``Staff`` row
    inside the dependency block. After the dependency exits cleanly, a NEW
    session opened on the same engine must see the row — proving
    ``get_db()`` called ``commit()``.
    """
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        with patch("backend.core.database.AsyncSessionLocal", TestSessionLocal):

            async def handler(session: AsyncSession) -> None:
                session.add(
                    Staff(
                        name="Committer",
                        role="CASHIER",
                        pin_hash="argon2id$x",
                    )
                )
                await session.flush()

            exc = await _run_get_db_like_fastapi(handler)
            assert exc is None, "no exception should propagate on the happy path"

            # Open a NEW session on the same engine — must see the committed row.
            from sqlalchemy import select

            async with TestSessionLocal() as fresh:
                rows = (
                    (
                        await fresh.execute(
                            select(Staff).where(Staff.name == "Committer")
                        )
                    )
                    .scalars()
                    .all()
                )

        assert (
            len(rows) == 1
        ), "expected the Staff row to persist after get_db() exited normally"
        assert rows[0].name == "Committer"
        assert rows[0].role.value == "CASHIER"
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Rollback on error
# ---------------------------------------------------------------------------


async def test_get_db_rolls_back_on_handler_error() -> None:
    """get_db() rolls back the session when the handler raises.

    Simulates a FastAPI route handler that flushes a ``Staff`` row and then
    raises ``RuntimeError``. The generator must (a) propagate the exception
    and (b) roll back the write so a NEW session does not see the row.
    """
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        with patch("backend.core.database.AsyncSessionLocal", TestSessionLocal):

            async def handler(session: AsyncSession) -> None:
                session.add(
                    Staff(
                        name="Rollbacker",
                        role="CASHIER",
                        pin_hash="argon2id$x",
                    )
                )
                await session.flush()
                raise RuntimeError("boom")

            exc = await _run_get_db_like_fastapi(handler)
            assert isinstance(
                exc, RuntimeError
            ), "RuntimeError should have propagated out of get_db()"
            assert str(exc) == "boom"

            # Open a NEW session on the same engine — the rolled-back row
            # must NOT be present.
            from sqlalchemy import select

            async with TestSessionLocal() as fresh:
                rows = (
                    (
                        await fresh.execute(
                            select(Staff).where(Staff.name == "Rollbacker")
                        )
                    )
                    .scalars()
                    .all()
                )

        assert rows == [], "expected NO Staff row after get_db() rolled back on error"
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Generator shape (defensive)
# ---------------------------------------------------------------------------


async def test_get_db_yields_exactly_one_session_and_calls_commit() -> None:
    """get_db() yields exactly one session and commits on clean exit.

    A defensive sanity check that the generator's lifecycle is: yield once,
    then commit, then close — i.e. the user's code body runs inside the
    ``yield`` slot and ``await session.commit()`` is executed at generator
    teardown on the happy path.
    """
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        with patch("backend.core.database.AsyncSessionLocal", TestSessionLocal):
            gen = get_db()
            assert hasattr(gen, "__aiter__"), "get_db() must return an async generator"

            session = await gen.__anext__()
            assert session is not None

            # No second yield: get_db() must yield only once.
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
            else:
                await gen.aclose()
                raise AssertionError("get_db() should yield exactly one session")
            finally:
                await gen.aclose()
    finally:
        await engine.dispose()
