# backend/tests/test_expense_schemas.py
from datetime import date

from backend.models._enums import ExpenseCategory
from backend.schemas.expense import ExpenseCreate, ExpenseResponse


def test_expense_create_valid():
    e = ExpenseCreate(
        date=date(2026, 8, 18),
        category=ExpenseCategory.RENT,
        amount_paise=5000000,
        note="August rent",
    )
    assert e.amount_paise == 5000000
    assert e.category == ExpenseCategory.RENT


def test_expense_create_rejects_negative_amount():
    import pydantic

    try:
        ExpenseCreate(date=date.today(), category=ExpenseCategory.RENT, amount_paise=-1)
    except pydantic.ValidationError:
        return
    raise AssertionError("expected ValidationError for negative amount")


def test_expense_response_from_orm():
    from datetime import UTC, datetime

    class FakeExpense:
        id = "exp1"
        date = date(2026, 8, 1)
        category = ExpenseCategory.ELECTRICITY
        amount_paise = 150000
        note = "Power bill"
        logged_by_staff_id = "staff1"
        created_at = datetime.now(UTC).isoformat()

    r = ExpenseResponse.model_validate(FakeExpense())
    assert r.id == "exp1"
    assert r.amount_paise == 150000
