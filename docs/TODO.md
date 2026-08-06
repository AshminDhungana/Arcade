# Todo

## Kiosk Overlay OFF — Call Staff Button Behavior

- [ ] **Kiosk overlay OFF state**: When the kiosk overlay setting is toggled off, hide all overlay UI elements except the Call Staff button, in every scenario (session start, mid-session, during gameplay, etc.)

- [ ] **Call Staff button visibility**
  - [ ] Button is hidden by default when overlay is off
  - [ ] Button appears only when the user moves the mouse to the right edge of the screen
  - [ ] Reuse the existing mouse-to-edge detection logic already implemented in the overlay — do not reimplement, just make it available/triggerable when overlay is off

- [ ] **Call Staff button functionality**
  - [ ] When visible, button must be fully clickable
  - [ ] Clicking it triggers the same "call staff" action as when the overlay is on
  - [ ] No difference in call-staff behavior/output between overlay-on and overlay-off states — only visibility/presentation changes

- [ ] **Regression checks**
  - [ ] Confirm no other overlay elements (menus, banners, controls, etc.) render or become interactable while overlay is off
  - [ ] Confirm button reveal/hide on mouse movement works consistently while user is actively playing/using the system (not just at idle/session start)
  - [ ] Confirm toggling overlay back ON restores full overlay UI as before

**Notes:**
- Mouse-edge-reveal logic already exists in the overlay component — this task is about detaching/exposing that specific piece of functionality so it still runs independently when the rest of the overlay is suppressed.
- Treat this as a visibility/composition change, not new logic — the call button's trigger detection and click handler should be shared/reused, not duplicated.


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
