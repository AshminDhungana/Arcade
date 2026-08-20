# AC-13 Linux Auto-Start Verification Checklist

**Date:** ___________ **Tester:** ___________ **Distro:** ___________

| # | Test | Expected | Actual |
|---|------|----------|--------|
| 1 | `systemctl --user enable --now arcade-agent.service` | Service enabled | |
| 2 | Reboot machine | Agent starts automatically | |
| 3 | Agent connects to server | WebSocket connected | |
| 4 | Kiosk overlay shows | AVAILABLE state | |
| 5 | Health metrics reported | Within 60s | |
| 6 | `journalctl --user -u arcade-agent` | No errors | |

**Sign-off:** ___________ **Date:** ___________
