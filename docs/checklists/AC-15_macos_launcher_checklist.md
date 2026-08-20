# AC-15 macOS Launcher Verification Checklist

**Date:** ___________ **Tester:** ___________

| # | Step | Expected | Actual |
|---|------|----------|--------|
| 1 | `brew install python-tk` | Tcl/Tk headers installed | |
| 2 | `python build.py --only launcher` | Produces `dist/Arcade Launcher.app/` | |
| 3 | Run `./dist/Arcade Launcher.app/Contents/MacOS/Arcade Launcher --self-test` | Self-test passes | |
| 4 | Tkinter UI renders | Activation/Setup/Main screens show | |
| 5 | "Start Server" spawns uvicorn subprocess | Server accessible on port 8742 | |
| 6 | "Stop Server" terminates uvicorn | Process exits cleanly | |

**Sign-off:** ___________ **Date:** ___________
