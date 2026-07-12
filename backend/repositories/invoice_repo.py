"""Invoice repository — CRUD + session lookup."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Invoice
from backend.models._enums import InvoiceLineItemType, PaymentMethod
from backend.models.invoice_line_item import InvoiceLineItem


async def create(
    db: AsyncSession,
    *,
    session_id: str,
    member_id: str | None = None,
    shift_id: str | None = None,
    time_charge_paise: int = 0,
    package_credit_used_paise: int = 0,
    discount_paise: int = 0,
    pos_total_paise: int = 0,
    total_paise: int = 0,
    payment_method: PaymentMethod | None = None,
) -> Invoice:
    invoice = Invoice(
        session_id=session_id,
        member_id=member_id,
        shift_id=shift_id,
        time_charge_paise=time_charge_paise,
        package_credit_used_paise=package_credit_used_paise,
        discount_paise=discount_paise,
        pos_total_paise=pos_total_paise,
        total_paise=total_paise,
        payment_method=payment_method,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)
    return invoice


async def get_by_id(db: AsyncSession, invoice_id: str) -> Invoice | None:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Invoice]:
    result = await db.execute(select(Invoice))
    return result.scalars().all()


async def update(db: AsyncSession, invoice: Invoice) -> Invoice:
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)
    return invoice


async def delete_by_id(db: AsyncSession, invoice_id: str) -> bool:
    invoice = await get_by_id(db, invoice_id)
    if invoice is None:
        return False
    await db.delete(invoice)
    await db.flush()
    return True


async def get_by_session(db: AsyncSession, session_id: str) -> Sequence[Invoice]:
    result = await db.execute(select(Invoice).where(Invoice.session_id == session_id))
    return result.scalars().all()


async def list_by_shift(db: AsyncSession, shift_id: str) -> Sequence[Invoice]:
    """Return all invoices recorded against *shift_id*."""
    result = await db.execute(select(Invoice).where(Invoice.shift_id == shift_id))
    return result.scalars().all()


# -- invoice line items --


async def list_line_items(
    db: AsyncSession, invoice_id: str
) -> Sequence[InvoiceLineItem]:
    result = await db.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id)
    )
    return result.scalars().all()


async def create_line_item(
    db: AsyncSession,
    *,
    invoice_id: str,
    type: InvoiceLineItemType,  # noqa: A002
    description: str,
    quantity: int,
    unit_price_paise: int,
    total_paise: int,
) -> InvoiceLineItem:
    item = InvoiceLineItem(
        invoice_id=invoice_id,
        type=type,
        description=description,
        quantity=quantity,
        unit_price_paise=unit_price_paise,
        total_paise=total_paise,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item
