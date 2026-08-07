# Todo

## Force Overlay Behavior
- [ ] Fix Force Overlay ON state — currently only a timer flashes in the center and disappears; it should show the **full overlay** (background + all overlay elements)
- [ ] Fix overlay dismissal logic — when overlay is closed via **server command** or **staff override**, only the **Call Staff** button (and its click handler) should remain on screen
- [ ] chek the implemented hover-to-reveal for Call Staff button — button stays hidden by default; when the user moves the mouse to the **top-bottom corner**, the button should fade/slide in and be clickable. This feature is implemented previously.

## 503 Errors on Rapid Overlay Toggle
- [ ] Reproduce: repeatedly toggling Force Overlay on/off triggers `503 Service Unavailable` on `POST /api/seats/seat_1/overlay`
- [ ] Check cascading impact — `GET /api/members` also returns `503` during/after this (likely shared connection pool, worker, or DB lock exhaustion)
- [ ] Identify root cause — probable race condition from overlapping/rapid-fire requests hitting the same seat resource without debounce or lock handling
- [ ] Add fix: debounce the toggle on the client (disable button briefly after click) and/or add request queuing or a mutex per seat on the server
- [ ] Add graceful error handling so a 503 doesn't leave overlay state out of sync between client and server

---

**Reference (from logs):** repeated `POST /api/seats/seat_1/overlay` calls returning `503` right after a `204 No Content` success, with `/api/members` also failing intermittently — worth checking if these share a resource/session in the backend.
