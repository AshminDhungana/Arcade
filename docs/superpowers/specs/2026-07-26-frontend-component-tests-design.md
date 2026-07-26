# Frontend Component Tests Design — Epic 8.2

**Date:** 2026-07-26
**Status:** Approved for implementation

---

## Context

Epic 8.2 (Frontend and E2E Testing) requires component tests for specific UI components. Current test suite: 291 tests passing across 68 files.

---

## Gap Analysis

| Test File | Existing Tests | Missing Tests |
|-----------|----------------|---------------|
| `SeatGrid.test.tsx` | 2 | Status colour-coding |
| `SeatCard.test.tsx` | 14 | Elapsed timer ticking; click → modal |
| `InvoicePanel.test.tsx` | 4 | **None (complete)** |
| `POSPanel.test.tsx` | 0 (missing) | All tests |
| `MemberSearch.test.tsx` | 1 | Member card render |
| `Login.test.tsx` | 7 | 5th failure lockout; success → token store |
| `useWebSocket.test.tsx` | 4 | **None (complete per TODO)** |

---

## Test Design

### 1. `POSPanel.test.tsx` (NEW FILE)

**Location:** `frontend/src/components/pos/POSPanel.test.tsx`

**Mock Strategy:**
- `useFeatureFlagStore` → `enable_pos`, `enable_inventory`
- `useMenu`, `useSessionItems` → React Query mock data
- `useAddPosItem`, `useRemovePosItem` → mutation mocks with `mutate` spy

**Tests:**

| Test | Purpose |
|------|---------|
| `renders null when enable_pos flag is false` | Feature flag gate |
| `renders MenuGrid and SessionTab when POS enabled` | Basic structure |
| `MenuItemCard is disabled when is_available=false` | Greyed-out via prop drilling |
| `clicking available item calls addMutation.mutate` | API integration |

---

### 2. `SeatGrid.test.tsx` — Additional Test

```typescript
it('applies correct status colour classes per seat status', () => {
  // Mock seats: AVAILABLE (green), IN_USE (blue), PAUSED (amber), MAINTENANCE (red)
  // Assert SeatCard receives correct status → className contains expected tailwind colours
})
```

---

### 3. `SeatCard.test.tsx` — Additional Tests

```typescript
it('shows elapsed timer that ticks for IN_USE seat', () => {
  vi.useFakeTimers();
  render(<SeatCard seat={{...mockSeat, status: IN_USE, started_at: '2024-01-01T00:00:00Z'}} onClick={vi.fn()} />);
  expect(screen.getByText('00:00:00')).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(61000));
  expect(screen.getByText('00:01:01')).toBeInTheDocument();
  vi.useRealTimers();
});

it('click triggers SeatActionModal via onClick handler', () => {
  const handleClick = vi.fn();
  render(<SeatCard seat={mockSeat} onClick={handleClick} />);
  fireEvent.click(screen.getByRole('button'));
  expect(handleClick).toHaveBeenCalledWith(mockSeat);
});
```

---

### 4. `MemberSearch.test.tsx` — Additional Test

```typescript
it('renders member card with name, phone, and tier badge', async () => {
  const onSelect = vi.fn();
  render(<MemberSearch onSelect={onSelect} />);
  fireEvent.change(screen.getByPlaceholderText(/Search members/i), { target: { value: 'jo' } });
  await waitFor(() => expect(screen.getByText('John')).toBeInTheDocument());
  expect(screen.getByText('9800000001')).toBeInTheDocument();
  expect(screen.getByText('BRONZE')).toBeInTheDocument();
});
```

---

### 5. `Login.test.tsx` — Additional Tests

```typescript
it('shows lockout message on 5th failed attempt', async () => {
  // Mock 4 sequential 401s, then 429 with retryAfter
  (login as Mock).mockRejectedValueOnce(new AuthError('Invalid', 401));
  (login as Mock).mockRejectedValueOnce(new AuthError('Invalid', 401));
  (login as Mock).mockRejectedValueOnce(new AuthError('Invalid', 401));
  (login as Mock).mockRejectedValueOnce(new AuthError('Invalid', 401));
  (login as Mock).mockRejectedValueOnce(new AuthError('Locked', 429, 900));

  renderWithRouter();
  // ... 5 submissions ...
  await waitFor(() => expect(screen.getByText(/account locked/i)).toBeInTheDocument());
});

it('stores token and staff in authStore on successful login', async () => {
  (login as Mock).mockResolvedValue({ access_token: 'tok123', staff: { id: 'STAFF-001', role: 'ADMIN' } });
  renderWithRouter();
  fireEvent.change(screen.getByLabelText(/staff id/i), { target: { value: 'STAFF-001' } });
  fireEvent.change(screen.getByLabelText(/pin/i), { target: { value: '1234' } });
  fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
  await waitFor(() => expect(mockStoreLogin).toHaveBeenCalledWith('tok123', { id: 'STAFF-001', role: 'ADMIN' }));
});
```

---

## Implementation Notes

- Reuse existing patterns: `QueryClientProvider` wrapper, `vi.mock` for hooks, `renderHook` for stores
- Use `vi.useFakeTimers()` + `act()` for timer tests
- Follow existing test file structure and naming conventions
- Run `npm test` after each file to verify

---

## Acceptance Criteria

- All new tests pass
- Total test count increases from 291 to ~300+
- No regressions in existing tests
- `npm test` exits with 0
