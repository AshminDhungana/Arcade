"""Expense CRUD router — Admin only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.repositories import expense_repo
from backend.schemas.expense import ExpenseCreate, ExpenseResponse

router = APIRouter(prefix="/expenses", tags=["expenses"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[Staff, Depends(require_admin)]


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: ExpenseCreate, db: DbDep, staff: AdminDep
) -> ExpenseResponse:
    expense = await expense_repo.create(
        db,
        date=body.date,
        category=body.category.value,
        amount_paise=body.amount_paise,
        note=body.note,
        logged_by_staff_id=staff.id,
    )
    return ExpenseResponse.model_validate(expense)


@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(db: DbDep, staff: AdminDep) -> list[ExpenseResponse]:
    expenses = await expense_repo.list(db)
    # expense_repo.list returns newest first (by created_at desc)
    return [ExpenseResponse.model_validate(e) for e in expenses]


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(expense_id: str, db: DbDep, staff: AdminDep) -> None:
    deleted = await expense_repo.delete_by_id(db, expense_id)
    if not deleted:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Expense not found")
