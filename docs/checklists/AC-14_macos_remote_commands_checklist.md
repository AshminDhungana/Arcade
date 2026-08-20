# AC-14 macOS Remote Commands Verification Checklist

**Date:** ___________ **Tester:** ___________

| # | Command | Method | Expected | Actual |
|---|---------|--------|----------|--------|
| 1 | Restart | `osascript -e 'tell app "System Events" to restart'` | Agent restarts, reconnects | |
| 2 | Shutdown | `osascript -e 'tell app "System Events" to shut down'` | Machine powers off | |
| 3 | Screenshot | `desktopCapturer` + `sharp` | JPEG ≤1280×720, q80 | |
| 4 | Fallback shutdown | `sudo shutdown -h now` (with sudoers) | Works if osascript fails | |

**sudoers entry:** `arcade-agent ALL=(ALL) NOPASSWD: /sbin/shutdown`

**Sign-off:** ___________ **Date:** ___________
