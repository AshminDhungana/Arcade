"""Custom SQLAlchemy types for the Arcade backend.

:mod:`StrEnumColumn` — stores a Python ``Enum`` member as its ``.value``
string in the database and returns the corresponding enum member on read.
This avoids the ``type '…' is not supported`` error that aiosqlite raises
when it receives an unhandled ``Enum`` instance.

Usage in a declarative model::

    from backend.models._types import StrEnumColumn

    class Zone(Base):
        status: Mapped[PricingModel] = mapped_column(
            StrEnumColumn(PricingModel, 25),
            nullable=False,
            default=PricingModel.PER_MINUTE,
        )

The generated DDL column type is still ``sqlalchemy.String``,
so no migration is required when switching from :class:`sqlalchemy.String`.
"""

from __future__ import annotations

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
