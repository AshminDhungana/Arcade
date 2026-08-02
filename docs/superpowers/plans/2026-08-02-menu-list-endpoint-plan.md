# Add GET /api/menu-items List Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `GET /api/menu-items` endpoint to the admin menu router that returns all menu items for admin management.

**Architecture:** Add a new route handler in `backend/api/routers/menu.py` that calls the existing `inventory_repo.list()` function and transforms results using the existing `_to_response()` helper. No schema changes needed.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, pytest-asyncio

## Global Constraints
- Uses existing `require_admin` dependency for authorization
- Returns `list[MenuItemResponse]` matching POS endpoint + `updated_at`
- No pagination initially (menu sizes <100 items)
- Frontend `useMenuItems()` hook already calls this endpoint — no frontend changes
- Follow existing code patterns in the router (type annotations, noqa comments, docstrings)

---

### Task 1: Add GET / list endpoint to menu router

**Files:**
- Modify: `backend/api/routers/menu.py:27-125`

**Interfaces:**
- Consumes: `inventory_repo.list(db)` → `Sequence[MenuItem]`, `_to_response(item)` → `MenuItemResponse`
- Produces: `list_menu_items()` function, `GET /api/menu-items` route returning `list[MenuItemResponse]`

- [ ] **Step 1: Write the failing test**

```python
# In backend/tests/test_menu_crud.py, add after TestAuthZoning class:

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
        assert all("updated_at" in item for item in data)

    async def test_list_empty(self, client: AsyncClient) -> None:
        # List when no items exist
        resp = await client.get("/api/menu-items")
        assert resp.status_code == 200
        assert resp.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd E:\Ongoing\ Projects\Arcade && python -m pytest backend/tests/test_menu_crud.py::TestList::test_list_menu_items -v`
Expected: FAIL with 404 (endpoint not found)

- [ ] **Step 3: Write minimal implementation**

Add to `backend/api/routers/menu.py` after `create_menu_item` function (after line 64):

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

Update the module docstring (lines 3-10) to include the new route:
```python
"""Menu item admin API router.

Routes::

    POST   /api/menu-items        -> create menu item (Admin)
    GET    /api/menu-items        -> list all (Admin)
    GET    /api/menu-items/{id}   -> get one (Admin)
    PUT    /api/menu-items/{id}   -> update (Admin)
    DELETE /api/menu-items/{id}   -> delete (Admin)

Reads for the POS UI remain at ``GET /api/pos/menu`` (cashier+).
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd E:\Ongoing\ Projects\Arcade && python -m pytest backend/tests/test_menu_crud.py::TestList -v`
Expected: PASS

- [ ] **Step 5: Run full test suite for menu router**

Run: `cd E:\Ongoing\ Projects\Arcade && python -m pytest backend/tests/test_menu_crud.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd E:\Ongoing\ Projects\Arcade
git add backend/api/routers/menu.py backend/tests/test_menu_crud.py
git commit -m "feat: add GET /api/menu-items list endpoint for admin menu management"
```

---

### Task 2: Verify frontend integration works

**Files:**
- No file changes needed (verification only)

**Interfaces:**
- Consumes: `useMenuItems()` hook in `frontend/src/api/settings.ts:628-634`
- Produces: Confirmation that Settings > Menu tab loads menu items

- [ ] **Step 1: Start backend server**

Run: `cd E:\Ongoing\ Projects\Arcade && python -m backend.main`
Expected: Server starts on port 8741

- [ ] **Step 2: Start frontend dev server**

Run: `cd E:\Ongoing\ Projects\Arcade\frontend && npm run dev`
Expected: Vite dev server starts

- [ ] **Step 3: Navigate to Settings > Menu tab in browser**

Open: `http://localhost:5173/settings` → click "Menu" tab
Expected: Menu items list loads without 404 errors

- [ ] **Step 4: Verify no 404 errors in backend logs**

Check backend console for `GET /api/menu-items` requests
Expected: 200 OK responses, no 404s

- [ ] **Step 5: Commit (if any config changes needed)**

```bash
cd E:\Ongoing\ Projects\Arcade
git commit -m "chore: verify frontend integration with new menu list endpoint"
```
