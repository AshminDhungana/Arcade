# Todo

## Quick Fixes
- [ ] Move the Call Staff button a little higher in the kisko overlay, as it is currently touching/overlapping the Windows taskbar start menu. And also the area where when mouse hover will make the button visible should be at the very edge of the screen, not above the button, at the very edge of the right botton when mouse is placed then the button shows. it should be such that when playing games user will not trigger the show of the button. 

## Task 2: Extra "Call Staff Available" notification shows up when it shouldn't

**Current behavior**
- Kiosk overlay is **off**.
- User moves mouse to the bottom-right corner.
- The Call Staff button appears (correct) **but** a "Call Staff Available" notification also appears above it (not correct).

**Expected behavior**
- Only the Call Staff button should appear on hover. The "Call Staff Available" notification should not be shown in this state.

**Steps to reproduce**
1. Ensure kiosk overlay is off.
2. Hover mouse over bottom-right corner of the screen.
3. Observe: Call Staff button + "Call Staff Available" notification both appear.

**Acceptance criteria**
- [ ] With overlay off, hovering the bottom-right corner shows only the Call Staff button.
- [ ] The "Call Staff Available" notification does not render in this state.
- [ ] Confirm the notification is still shown correctly in whatever state it *is* meant for (so this fix doesn't just delete it globally) — flag if unsure where else it's used.


