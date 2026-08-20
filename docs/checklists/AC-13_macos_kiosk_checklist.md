# AC-13 macOS Kiosk Overlay Verification Checklist

**Date:** ___________ **Tester:** ___________ **macOS Version:** ___________

| # | Test | Expected | Actual | Notes |
|---|------|----------|--------|-------|
| 1 | Overlay displays full-screen | ✅ | | |
| 2 | Cmd+Q blocked | ✅ | | |
| 3 | Cmd+W blocked | ✅ | | |
| 4 | Cmd+H blocked | ✅ | | |
| 5 | Cmd+M blocked | ✅ | | |
| 6 | Cmd+Tab | ❌ OS-protected | | Document |
| 7 | Cmd+Space (Spotlight) | ❌ OS-protected | | Document |
| 8 | Cmd+Opt+Esc (Force Quit) | ❌ OS-protected | | Document |
| 9 | Ctrl+Cmd+Power | ❌ OS-protected | | Document |
| 10 | Screen Recording permission granted | ✅ | | Required for screenshots |
| 11 | Accessibility permission granted | ✅ | | Required for shortcut blocking |
| 12 | Session start → overlay hides | ✅ | | |
| 13 | Session end → overlay shows | ✅ | | |
| 14 | Screenshot request returns image | ✅ | | |
| 15 | Auto-start survives reboot | ✅ | | |

**Sign-off:** ___________ **Date:** ___________
