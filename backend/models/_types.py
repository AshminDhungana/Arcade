"""Custom SQLAlchemy types for the Arcade backend.

:mod:`StrEnumColumn` — stores a Python ``Enum`` member as its ``.value``
string in the database and returns the corresponding enum member on read.
This avoids the ``type '…' is not supported`` error that aiosqlite raises
when it receives an unhandled ``Enum`` instance.

:mod:`UTCDatetime` — stores ``datetime`` objects as UTC ISO strings and
guarantees timezone-aware (UTC) datetimes on read. SQLite does not have a
native timezone-aware datetime type, so this decorator handles the round-trip
transparently.

Usage in a declarative model::

    from backend.models._types import StrEnumColumn, UTCDatetime

    class Zone(Base):
        status: Mapped[PricingModel] = mapped_column(
            StrEnumColumn(PricingModel, 25),
            nullable=False,
            default=PricingModel.PER_MINUTE,
        )
        created_at: Mapped[datetime] = mapped_column(
            UTCDatetime, nullable=False, default=lambda: datetime.now(UTC)
        )
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class StrEnumColumn(TypeDecorator):  # type: ignore[type-arg]  # impl set below
    """TypeDecorator that stores a Python :class:`Enum` member as a string.

    Parameters
    ----------
    enum_type:
        The ``Enum`` class whose members are persisted.
    max_length:
        Maximum length of the backing ``VARCHAR`` column.  Defaults to 255.
    """

    impl = String
    cache_ok = True

    def __init__(
        self,
        enum_type: type[Enum],
        max_length: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.enum_type = enum_type
        length = max_length if max_length is not None else 255
        super().__init__(length, **kwargs)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """Serialize an enum member (or string) to a plain string."""
        if value is None:
            return None
        if isinstance(value, self.enum_type):
            return value.value
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Deserialize a string back to the enum member."""
        if value is None:
            return None
        return self.enum_type(value)


class UTCDatetime(TypeDecorator[datetime]):
    """TypeDecorator that stores UTC datetimes as ISO strings and ensures
    timezone-aware (UTC) datetimes on read.

    SQLite has no native timezone-aware datetime type. This decorator
    serializes to ISO 8601 with 'Z' suffix (UTC) and deserializes to a
    timezone-aware ``datetime`` with ``tzinfo=UTC``.
    """

    impl = String
    cache_ok = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(length=32, **kwargs)  # ISO UTC format fits in 32 chars

    def process_bind_param(self, value: datetime | None, dialect: Any) -> str | None:
        """Serialize a timezone-aware datetime to a fixed-width UTC ISO string.

        Uses ``strftime`` with 6-digit microseconds + ``Z`` so that every
        stored value has identical width. This keeps lexicographic (TEXT)
        comparison in ``print_job_repo.list_due`` (``next_retry_at <= now``)
        robust regardless of microsecond precision — a whole-second timestamp
        (``microsecond=0``) would otherwise sort *after* a microsecond-precise
        one under ISO ``isoformat()``, which drops the ``.%f`` segment.
        """
        if value is None:
            return None
        # Ensure value is timezone-aware (UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        elif value.tzinfo != UTC:
            value = value.astimezone(UTC)
        # Fixed-width ISO format with 'Z' suffix for UTC (always 6-digit µs)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def process_result_value(self, value: str | None, dialect: Any) -> datetime | None:
        """Deserialize ISO string to timezone-aware UTC datetime."""
        if value is None:
            return None
        # Parse ISO string and ensure UTC timezone
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
