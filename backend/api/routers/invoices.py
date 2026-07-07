"""Invoice API router.

Routes::

    GET /api/invoices/{id}      → get invoice detail (cashier+)
    GET /api/invoices/{id}/pdf  → print-friendly HTML receipt (cashier+)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Template as JinjaTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.config import get_config
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.repositories import invoice_repo
from backend.schemas.invoice import InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["invoices"])

# ---------------------------------------------------------------------------
# HTML Receipt Template (Jinja2)
# ---------------------------------------------------------------------------

_HTML_TPL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Receipt</title>
  <style>
    body { font-family: 'Courier New', monospace; width: 320px; margin: 20px auto; }
    h1 { text-align: center; font-size: 18px; margin: 0; }
    .center { text-align: center; }
    .separator { border-top: 1px dashed #000; margin: 8px 0; }
    .row { display: flex; justify-content: space-between; font-size: 14px; }
    .bold { font-weight: bold; }
    .total { font-size: 16px; font-weight: bold; margin-top: 10px; }
    @media print { body { margin: 0; } }
  </style>
</head>
<body>
  <h1>{{ cafe_name }}</h1>
  <div class="separator"></div>
  {% if seat_name %}
  <div class="row"><span>Seat:</span><span>{{ seat_name }}</span></div>
  {% endif %}
  <div class="row"><span>Date:</span><span>{{ date }}</span></div>
  <div class="separator"></div>
  {% for item in line_items %}
  <div class="row">
    <span>{{ item.description }} x{{ item.quantity }}</span>
    <span>Rs. {{ "%.2f"|format(item.total_paise / 100) }}</span>
  </div>
  {% endfor %}
  <div class="separator"></div>
  {% for total in totals %}
  <div class="row {% if total.bold %}total{% endif %}">
    <span>{{ total.label }}</span><span>{{ total.value }}</span>
  </div>
  {% endfor %}
  <div class="separator"></div>
  <p class="center">Thank you!</p>
  <script>
    window.onload = function() { setTimeout(function() { window.print(); }, 500); };
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> InvoiceResponse:
    """Get a single invoice by ID (cashier+)."""
    invoice = await invoice_repo.get_by_id(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/{invoice_id}/pdf",
    response_class=HTMLResponse,
)
async def get_invoice_pdf(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> str:
    """Return a print-friendly HTML receipt (cashier+).

    Triggers browser print via inline JavaScript.
    """
    invoice = await invoice_repo.get_by_id(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    config = get_config()
    cafe_name = config.cafe_name

    # Build line item data for template
    line_items: list[dict[str, object]] = []
    for li in invoice.line_items or []:
        line_items.append(
            {
                "description": li.description,
                "quantity": li.quantity,
                "total_paise": li.total_paise,
            }
        )

    # Build totals section
    totals: list[dict[str, object]] = []
    if invoice.time_charge_paise and invoice.time_charge_paise > 0:
        totals.append(
            {
                "label": "Time charge:",
                "value": f"Rs. {invoice.time_charge_paise / 100:.2f}",
                "bold": False,
            }
        )
    if invoice.discount_paise and invoice.discount_paise > 0:
        totals.append(
            {
                "label": "Discount:",
                "value": f"-Rs. {invoice.discount_paise / 100:.2f}",
                "bold": False,
            }
        )
    totals.append(
        {
            "label": "TOTAL:",
            "value": f"Rs. {invoice.total_paise / 100:.2f}",
            "bold": True,
        }
    )
    totals.append(
        {
            "label": "Paid by:",
            "value": (
                invoice.payment_method.value if invoice.payment_method else "CASH"
            ),
            "bold": False,
        }
    )

    html = JinjaTemplate(_HTML_TPL).render(
        cafe_name=cafe_name,
        seat_name="",
        date=invoice.created_at.strftime("%Y-%m-%d %H:%M"),
        duration="",
        line_items=line_items,
        totals=totals,
    )

    return str(html)
