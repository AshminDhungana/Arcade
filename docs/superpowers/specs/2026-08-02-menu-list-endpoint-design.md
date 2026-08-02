# Design: Add GET /api/menu-items List Endpoint

## Problem
The Settings > Menu tab in the frontend calls `GET /api/menu-items` to list all menu items for admin management. The backend's menu router (`backend/api/routers/menu.py`) only implements:
- `POST /api/menu-items` — create
- `GET /api/menu-items/{id}` — get one
- `PUT /api/menu-items/{id}` — update
- `DELETE /api/menu-items/{id}` — delete

There is no `GET /api/menu-items` (list all) endpoint, causing 404 errors in the logs.

The POS endpoint `GET /api/pos/menu` exists but requires cashier role + `enable_pos` feature flag, making it unsuitable for admin menu management.

## Solution
Add a `GET /api/menu-items` endpoint to the admin menu router that returns all menu items.

## Changes

### 1. `backend/api/routers/menu.py`
Add new route after `create_menu_item`:
```python
@router.get(
    "",
    response_model=list[MenuItemResponse],
    summary="List all menu items",
)
async def list_menu_items(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[None, Depends(require_admin)] = None,  # noqa: B008
) -> list[MenuItemResponse]:
    """List all menu items. Admin only."""
    items = await inventory_repo.list(db)
    return [_to_response(item) for item in items]
```

Update the module docstring to include:
```
GET    /api/menu-items        -> list all (Admin)
```

### 2. `backend/tests/test_menu_crud.py`
Add test case for the new list endpoint:
```python
class TestList:
    async def test_list_menu_items(self, client: AsyncClient) -> None:
        # Create a few items
        await client.post("/api/menu-items", json={"name": "Item 1", "price_paise": 1000})
        await client.post("/api/menu-items", json={"name": "Item 2", "price_paise": 2000})

        resp = await client.get("/api/menu-items")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        assert all("id" in item for item in data)
```

## Response Format
Returns `list[MenuItemResponse]` matching the POS endpoint shape plus `updated_at`:
```json
[
  {
    "id": "uuid",
    "name": "Cola",
    "category": "Beverages",
    "price_paise": 5000,
    "stock_quantity": 50,
    "low_stock_threshold": 10,
    "is_available": true,
    "updated_at": "2026-08-02T10:30:00Z"
  }
]
```

## Security
- Requires admin role (via existing `require_admin` dependency)
- Returns 403 for cashier/non-admin users
- Returns 401 for unauthenticated requests

## Pagination
Not implemented initially — typical menu size is <100 items. Can add `limit`/`offset` query params later if needed.

## Frontend
No changes required. The `useMenuItems()` hook in `frontend/src/api/settings.ts` already calls `GET /api/menu-items` and expects `MenuItem[]` (compatible with `MenuItemResponse`).

## Testing
- Unit test for the new endpoint (added to `test_menu_crud.py`)
- Existing frontend integration will work once endpoint exists
