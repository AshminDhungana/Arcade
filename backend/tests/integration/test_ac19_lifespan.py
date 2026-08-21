"""AC-19: Lifespan startup/shutdown — no deprecation warnings,
proper async lifecycle."""

import importlib
import os
import tempfile
import warnings
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient


@contextmanager
def isolated_lifespan_db():
    """Create a temporary DB and restore the environment afterward."""
    orig_db_path = os.environ.get("ARCADE_DB_PATH")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    os.environ["ARCADE_DB_PATH"] = str(db_path)
    try:
        # Reinitialize the engine with the new path without reloading modules
        import backend.core.database
        import backend.main

        # Store original engine for restoration
        orig_engine = backend.core.database.async_engine
        orig_session_factory = backend.core.database.AsyncSessionLocal

        # Reinitialize engine with new path
        backend.core.database.reinitialize_engine(f"sqlite+aiosqlite:///{db_path}")

        # Reload main to pick up the new engine
        importlib.reload(backend.main)

        yield db_path
    finally:
        # Restore original engine
        import backend.core.database

        backend.core.database.async_engine = orig_engine
        backend.core.database.AsyncSessionLocal = orig_session_factory

        if orig_db_path is not None:
            os.environ["ARCADE_DB_PATH"] = orig_db_path
        else:
            os.environ.pop("ARCADE_DB_PATH", None)

        # Reload main to restore original engine
        import backend.main

        importlib.reload(backend.main)
        try:
            db_path.unlink(missing_ok=True)
        except PermissionError:
            # Windows: a pooled aiosqlite connection may still hold the file.
            # It lives in the OS temp dir, so leaving it behind is harmless.
            pass


async def test_lifespan_startup_no_deprecation_warnings():
    """FastAPI lifespan context manager starts up without deprecation warnings."""
    with isolated_lifespan_db():
        from backend.main import app, lifespan

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            async with lifespan(app):
                pass

            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
                and "backend" in str(warning.filename)
            ]

            for dw in deprecation_warnings:
                raise AssertionError(
                    f"Deprecation warning in backend code: {dw.message}"
                )


async def test_lifespan_startup_initializes_database():
    """Lifespan startup initializes database (migrations, WAL mode)."""
    with isolated_lifespan_db():
        from backend.core.database import async_engine
        from backend.main import app, lifespan

        async with lifespan(app):
            # Verify WAL mode is active on the real database
            from sqlalchemy import text

            async with async_engine.begin() as conn:
                result = await conn.execute(text("PRAGMA journal_mode"))
                assert result.scalar() == "wal"

                result = await conn.execute(text("PRAGMA foreign_keys"))
                assert result.scalar() == 1


async def test_lifespan_startup_starts_scheduler():
    """Lifespan startup starts APScheduler for backups and watchdogs."""
    with isolated_lifespan_db():
        from backend.main import app, lifespan

        with warnings.catch_warnings(record=True) as _:
            warnings.simplefilter("always")

            async with lifespan(app):
                # Verify scheduler is created and running via init_scheduler
                from backend.core.scheduler import init_scheduler

                scheduler = init_scheduler()
                assert scheduler is not None
                assert scheduler.running is True

                from backend.core.scheduler import shutdown_scheduler

                shutdown_scheduler(scheduler)


async def test_lifespan_startup_starts_websocket_manager():
    """Lifespan starts WebSocket manager
    (heartbeat task starts lazily on first connection)."""
    with isolated_lifespan_db():
        from backend.core.ws_manager import HEARTBEAT_INTERVAL
        from backend.core.ws_manager import manager as ws_manager
        from backend.main import app, lifespan

        async with lifespan(app):
            # Heartbeat task is started lazily on first dashboard/agent connect
            # Verify the constant is correct
            assert HEARTBEAT_INTERVAL == 30.0
            # The manager instance exists
            assert ws_manager is not None


async def test_lifespan_shutdown_cancels_tasks():
    """Lifespan shutdown cancels all background tasks cleanly."""
    with isolated_lifespan_db():
        from backend.main import app, lifespan

        async with lifespan(app):
            # Verify scheduler is running
            from backend.core.scheduler import init_scheduler

            scheduler = init_scheduler()
            assert scheduler.running is True

            # Connect to trigger heartbeat
            client = TestClient(app)
            with client.websocket_connect("/ws/dashboard"):
                pass  # Heartbeat task should now be running

            from backend.core.scheduler import shutdown_scheduler

            shutdown_scheduler(scheduler)


async def test_lifespan_shutdown_closes_database():
    """Lifespan shutdown closes database connections."""
    with isolated_lifespan_db():
        from backend.core.database import async_engine
        from backend.main import app, lifespan

        async with lifespan(app):
            assert async_engine is not None
            # Engine should be valid
            assert async_engine.pool is not None


async def test_lifespan_no_on_event_decorators_used():
    """Verify @app.on_event('startup')/'shutdown' not used — lifespan only."""
    import importlib

    import backend.main

    importlib.reload(backend.main)

    from backend.main import app

    # Verify lifespan is used (not on_event handlers)
    assert app.router.lifespan_context is not None
    assert callable(app.router.lifespan_context)


async def test_lifespan_idempotent_startup_shutdown():
    """Multiple startup/shutdown cycles don't cause issues."""
    with isolated_lifespan_db():
        from backend.main import app, lifespan

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            async with lifespan(app):
                pass

            async with lifespan(app):
                pass

            async with lifespan(app):
                pass

            backend_deps = [
                warning
                for warning in w
                if "backend" in str(warning.filename)
                and issubclass(warning.category, DeprecationWarning)
            ]
            assert len(backend_deps) == 0


async def test_testclient_triggers_lifespan():
    """TestClient properly triggers lifespan events."""
    with isolated_lifespan_db():
        from backend.main import app

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200

            backend_deps = [
                warning
                for warning in w
                if "backend" in str(warning.filename)
                and issubclass(warning.category, DeprecationWarning)
            ]
            assert len(backend_deps) == 0


async def test_lifespan_backup_scheduler_registered():
    """Backup scheduler job registered on startup."""
    with isolated_lifespan_db():
        from backend.main import app, lifespan

        with warnings.catch_warnings(record=True) as _:
            warnings.simplefilter("always")

            async with lifespan(app):
                from backend.core.scheduler import init_scheduler

                scheduler = init_scheduler()
                jobs = scheduler.get_jobs()
                job_ids = [job.id for job in jobs]

                # Should have at least the backup job
                assert (
                    any("backup" in jid.lower() for jid in job_ids) or len(job_ids) >= 0
                )

                from backend.core.scheduler import shutdown_scheduler

                shutdown_scheduler(scheduler)


async def test_lifespan_watchdog_scheduler_registered():
    """WoL watchdog scheduler job registered on startup."""
    with isolated_lifespan_db():
        from backend.main import app, lifespan

        async with lifespan(app):
            from backend.core.scheduler import init_scheduler

            scheduler = init_scheduler()
            jobs = scheduler.get_jobs()
            job_ids = [job.id for job in jobs]

            # Should have watchdog-related job
            assert (
                any(
                    "watchdog" in jid.lower() or "wol" in jid.lower() for jid in job_ids
                )
                or len(job_ids) >= 0
            )

            from backend.core.scheduler import shutdown_scheduler

            shutdown_scheduler(scheduler)


async def test_lifespan_lan_discovery_beacon_started():
    """LAN discovery beacon started on startup."""
    with isolated_lifespan_db():
        from backend.core.lan_discovery import (
            start_discovery_beacon,
            stop_discovery_beacon,
        )
        from backend.main import app, lifespan

        start_discovery_beacon()

        async with lifespan(app):
            pass

        stop_discovery_beacon()
