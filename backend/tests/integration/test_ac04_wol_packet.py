"""AC-04: WoL magic packet structure correctness."""

import socket
from unittest.mock import MagicMock, patch


async def test_wol_magic_packet_structure(
    integration_db, seeded_zone, seeded_seat, admin_staff
):
    """WoL magic packet has correct structure: 6 bytes 0xFF +
    16 repetitions of 6-byte MAC."""
    from backend.services.wol_service import send_magic_packet

    # Set a MAC address on the seat
    seeded_seat.mac_address = "aa:bb:cc:dd:ee:ff"
    await integration_db.commit()

    # Capture the UDP packet sent
    captured_packet = {}

    def capture_sendto(packet, addr):
        captured_packet["data"] = packet
        captured_packet["addr"] = addr

    with patch("socket.socket") as mock_socket_class:
        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = capture_sendto
        mock_socket_class.return_value = mock_sock

        # Call the function
        send_magic_packet("aa:bb:cc:dd:ee:ff")

        # Verify the packet structure
        packet = captured_packet["data"]
        assert packet is not None, "Packet should be captured"

        # Check length: 6 bytes 0xFF + 16 * 6 bytes MAC = 6 + 96 = 102 bytes
        assert (
            len(packet) == 102
        ), f"Packet length should be 102 bytes, got {len(packet)}"

        # Check first 6 bytes are 0xFF
        assert packet[:6] == b"\xff" * 6, "First 6 bytes should be 0xFF"

        # Check 16 repetitions of MAC
        mac_bytes = bytes.fromhex("aabbccddeeff")
        for i in range(16):
            start = 6 + i * 6
            end = start + 6
            assert packet[start:end] == mac_bytes, f"MAC repetition {i+1} mismatch"

        # Check socket was created with correct params
        mock_socket_class.assert_called_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_sock.setsockopt.assert_called_with(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1
        )
        mock_sock.sendto.assert_called_once()
        args = mock_sock.sendto.call_args[0]
        assert args[1] == ("255.255.255.255", 9), "Default broadcast address and port 9"


async def test_wol_service_sends_packet_on_boot(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Integration test: booting a seat sends WoL magic packet."""
    from backend.models import SeatStatus
    from backend.services import wol_service

    seeded_seat.mac_address = "11:22:33:44:55:66"
    seeded_seat.status = SeatStatus.OFFLINE
    await integration_db.commit()

    captured_packet = {}

    def capture_sendto(packet, addr):
        captured_packet["data"] = packet
        captured_packet["addr"] = addr

    with patch("socket.socket") as mock_socket_class:
        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = capture_sendto
        mock_socket_class.return_value = mock_sock

        # Trigger WoL via service
        result = await wol_service.send_wol_to_seat(
            integration_db, seeded_seat.id, admin_staff
        )

        # Verify packet was sent
        assert captured_packet["data"] is not None
        packet = captured_packet["data"]
        assert len(packet) == 102
        assert packet[:6] == b"\xff" * 6
        mac_bytes = bytes.fromhex("112233445566")
        for i in range(16):
            start = 6 + i * 6
            assert packet[start : start + 6] == mac_bytes

        # Verify seat status updated to BOOTING
        assert result.status == SeatStatus.BOOTING
        assert result.wol_attempts == 1
