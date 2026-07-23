"""Tests for printer_uri support in print service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class _DummyUSBPrinter:
    """Mock USB printer that tracks constructor args."""

    def __init__(self, vendor: int, product: int):
        self.vendor = vendor
        self.product = product
        self.closed = False

    def text(self, text: str) -> None:
        pass

    def cut(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class _DummyNetworkPrinter:
    """Mock network printer that tracks constructor args."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.closed = False

    def text(self, text: str) -> None:
        pass

    def cut(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def _make_config(
    printer_type: str = "usb",
    printer_uri: str | None = None,
    printer_usb_vendor: str = "0x04b8",
    printer_usb_product: str = "0x0202",
):
    cfg = MagicMock()
    cfg.cafe_name = "Test"
    cfg.printer_type = printer_type
    cfg.printer_usb_vendor = printer_usb_vendor
    cfg.printer_usb_product = printer_usb_product
    cfg.printer_uri = printer_uri
    return cfg


class TestGetPrinterWithURI:
    """Test _get_printer uses printer_uri when available."""

    def test_usb_with_uri(self) -> None:
        """USB printer_uri overrides vendor/product."""
        from backend.services import print_service as ps

        cfg = _make_config(printer_type="usb", printer_uri="usb://USB001")

        with patch(
            "escpos.printer.Usb", return_value=_DummyUSBPrinter(0x04B8, 0x0202)
        ) as mock_usb:
            printer = ps._get_printer(cfg)

            # Should parse USB URI and use it
            mock_usb.assert_called_once()
            assert printer is not None

    def test_network_with_socket_uri(self) -> None:
        """Network printer with socket:// URI."""
        from backend.services import print_service as ps

        cfg = _make_config(
            printer_type="network", printer_uri="socket://192.168.1.100:9100"
        )

        with patch(
            "escpos.printer.Network",
            return_value=_DummyNetworkPrinter("192.168.1.100", 9100),
        ) as mock_network:
            printer = ps._get_printer(cfg)

            mock_network.assert_called_once_with("192.168.1.100", 9100)
            assert printer is not None

    def test_network_with_ipp_uri(self) -> None:
        """Network printer with ipp:// URI."""
        from backend.services import print_service as ps

        cfg = _make_config(
            printer_type="network", printer_uri="ipp://192.168.1.100:631/ipp/print"
        )

        with patch(
            "escpos.printer.Network",
            return_value=_DummyNetworkPrinter("192.168.1.100", 631),
        ) as mock_network:
            printer = ps._get_printer(cfg)

            # Should extract host and port from IPP URI
            mock_network.assert_called_once_with("192.168.1.100", 631)
            assert printer is not None

    def test_network_with_http_uri(self) -> None:
        """Network printer with http:// URI (uses port 80 default)."""
        from backend.services import print_service as ps

        cfg = _make_config(
            printer_type="network", printer_uri="http://printer.local/ipp/print"
        )

        with patch(
            "escpos.printer.Network",
            return_value=_DummyNetworkPrinter("printer.local", 80),
        ) as mock_network:
            printer = ps._get_printer(cfg)

            mock_network.assert_called_once_with("printer.local", 80)
            assert printer is not None

    def test_network_with_https_uri(self) -> None:
        """Network printer with https:// URI (uses port 443 default)."""
        from backend.services import print_service as ps

        cfg = _make_config(
            printer_type="network",
            printer_uri="https://printer.example.com/ipp/print",
        )

        with patch(
            "escpos.printer.Network",
            return_value=_DummyNetworkPrinter("printer.example.com", 443),
        ) as mock_network:
            printer = ps._get_printer(cfg)

            mock_network.assert_called_once_with("printer.example.com", 443)
            assert printer is not None

    def test_network_fallback_without_uri(self) -> None:
        """Without printer_uri, falls back to default IP:port."""
        from backend.services import print_service as ps

        cfg = _make_config(printer_type="network", printer_uri=None)

        with patch(
            "escpos.printer.Network",
            return_value=_DummyNetworkPrinter("127.0.0.1", 9100),
        ) as mock_network:
            printer = ps._get_printer(cfg)

            mock_network.assert_called_once_with("127.0.0.1", 9100)
            assert printer is not None

    def test_usb_fallback_without_uri(self) -> None:
        """USB without URI falls back to vendor/product."""
        from backend.services import print_service as ps

        cfg = _make_config(printer_type="usb", printer_uri=None)

        with patch(
            "escpos.printer.Usb", return_value=_DummyUSBPrinter(0x04B8, 0x0202)
        ) as mock_usb:
            printer = ps._get_printer(cfg)

            mock_usb.assert_called_once_with(0x04B8, 0x0202)
            assert printer is not None

    def test_usb_uri_parses_vendor_product(self) -> None:
        """USB URI like usb://0x04b8:0x0202 extracts vendor/product."""
        from backend.services import print_service as ps

        cfg = _make_config(printer_type="usb", printer_uri="usb://0x04b8:0x0202")

        with patch(
            "escpos.printer.Usb", return_value=_DummyUSBPrinter(0x04B8, 0x0202)
        ) as mock_usb:
            printer = ps._get_printer(cfg)

            mock_usb.assert_called_once_with(0x04B8, 0x0202)
            assert printer is not None

    def test_unknown_scheme_falls_back(self) -> None:
        """Unknown URI scheme falls back to defaults."""
        from backend.services import print_service as ps

        cfg = _make_config(printer_type="network", printer_uri="ftp://printer.local")

        with patch(
            "escpos.printer.Network",
            return_value=_DummyNetworkPrinter("127.0.0.1", 9100),
        ) as mock_network:
            printer = ps._get_printer(cfg)

            mock_network.assert_called_once_with("127.0.0.1", 9100)
            assert printer is not None


class TestParsePrinterURI:
    """Test URI parsing helper if extracted."""

    def test_parse_usb_uri(self) -> None:
        from backend.services.print_service import _parse_printer_uri

        result = _parse_printer_uri("usb://USB001")
        assert result["scheme"] == "usb"
        assert result["path"] == "USB001"

    def test_parse_socket_uri(self) -> None:
        from backend.services.print_service import _parse_printer_uri

        result = _parse_printer_uri("socket://192.168.1.100:9100")
        assert result["scheme"] == "socket"
        assert result["host"] == "192.168.1.100"
        assert result["port"] == 9100

    def test_parse_ipp_uri(self) -> None:
        from backend.services.print_service import _parse_printer_uri

        result = _parse_printer_uri("ipp://192.168.1.100:631/ipp/print")
        assert result["scheme"] == "ipp"
        assert result["host"] == "192.168.1.100"
        assert result["port"] == 631

    def test_parse_http_uri(self) -> None:
        from backend.services.print_service import _parse_printer_uri

        result = _parse_printer_uri("http://printer.local:8080/print")
        assert result["scheme"] == "http"
        assert result["host"] == "printer.local"
        assert result["port"] == 8080

    def test_parse_https_uri_default_port(self) -> None:
        from backend.services.print_service import _parse_printer_uri

        result = _parse_printer_uri("https://printer.example.com/print")
        assert result["scheme"] == "https"
        assert result["host"] == "printer.example.com"
        assert result["port"] == 443

    def test_parse_lpd_uri(self) -> None:
        from backend.services.print_service import _parse_printer_uri

        result = _parse_printer_uri("lpd://192.168.1.100/queue")
        assert result["scheme"] == "lpd"
        assert result["host"] == "192.168.1.100"
        assert result["port"] == 515  # LPD default
