"""InvoiceLineItem model — individual line items on an invoice."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import InvoiceLineItemType


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    invoice_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("invoices.id"), nullable=False
    )
    type: Mapped[InvoiceLineItemType] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price_paise: Mapped[int]
    total_paise: Mapped[int]
