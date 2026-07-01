from datetime import UTC, datetime

from backend.schemas.pos import MenuItemCreate, MenuItemResponse, SessionPOSItemCreate


class TestMenuItemCreate:
    def test_valid(self) -> None:
        m = MenuItemCreate(name="Cola", price_paise=5000)
        assert m.name == "Cola"
        assert m.price_paise == 5000
        assert m.is_available is True


class TestSessionPOSItemCreate:
    def test_valid(self) -> None:
        p = SessionPOSItemCreate(
            session_id="s1", menu_item_id="m1", unit_price_paise=5000
        )
        assert p.quantity == 1  # default


class TestMenuItemResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeItem:
            id = "item1"
            name = "Cola"
            category = "Drinks"
            price_paise = 5000
            stock_quantity = 10
            low_stock_threshold = 5
            is_available = True
            updated_at = now

        r = MenuItemResponse.model_validate(FakeItem())
        assert r.id == "item1"
