# Events & Tournaments Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the frontend gaps for Section J — Events & Tournaments: enhanced participant registration (member + walk-in with seat assignment) and Dashboard events widget.

**Architecture:** Reuse existing backend APIs (fully implemented). Add two new React Query hooks for members/seats, rewrite RegisterParticipantModal with mode toggle, create EventsWidget component for Dashboard, add test coverage.

**Tech Stack:** React 18, TypeScript, TanStack Query v5, Vitest, React Testing Library, Tailwind CSS

## Global Constraints

- Follow existing code patterns in `frontend/src/components/events/` and `frontend/src/api/`
- Use `useAuthStore` for token, `toastStore` for notifications
- Monetary values: paise in API, rupees in UI (×100 / ÷100)
- Feature flag: `enable_tournaments` gates entire events router (503 when off)
- Backend validates seat status on registration; frontend shows real-time via WS
- Commit after each task with conventional commit messages

---

### Task 1: Add `useActiveMembers` and `useAvailableSeats` hooks

**Files:**
- Modify: `frontend/src/api/members.ts` (add hook after line 115)
- Modify: `frontend/src/api/seats.ts` (add hook after line 144)
- Test: `frontend/src/api/members.test.tsx` (new)
- Test: `frontend/src/api/seats.test.tsx` (new)

**Interfaces:**
- Consumes: existing `listMembers` function, `fetchSeats` function, `useAuthStore`
- Produces: `useActiveMembers()` → `Member[]` (filtered `is_active=true`), `useAvailableSeats()` → `Seat[]` (filtered `status in ['AVAILABLE','ONLINE']`)

- [ ] **Step 1: Write failing test for `useActiveMembers`**

```tsx
// frontend/src/api/members.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useActiveMembers, listMembers } from './members';
import { useAuthStore } from '@/store/authStore';

const MEMBERS = [
  { id: 'm1', name: 'Alice', phone: '9800000001', wallet_balance_paise: 5000, tier: 'BRONZE', is_active: true },
  { id: 'm2', name: 'Bob', phone: '9800000002', wallet_balance_paise: 3000, tier: 'SILVER', is_active: true },
  { id: 'm3', name: 'Carol', phone: '9800000003', wallet_balance_paise: 1000, tier: 'BRONZE', is_active: false },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useActiveMembers', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('fetches and filters to active members only', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const { result } = renderHook(() => useActiveMembers(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.length).toBe(2);
    expect(result.current.data?.every(m => m.is_active)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/members.test.tsx`
Expected: FAIL - `useActiveMembers` not exported

- [ ] **Step 3: Implement `useActiveMembers` hook in `members.ts`**

```typescript
// Add after useMembers hook (around line 115)
export function useActiveMembers() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['members', 'active'],
    queryFn: async () => {
      const all = await listMembers({}, token);
      return all.filter((m) => m.is_active);
    },
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/members.test.tsx`
Expected: PASS

- [ ] **Step 5: Write failing test for `useAvailableSeats`**

```tsx
// frontend/src/api/seats.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useAvailableSeats } from './seats';
import { useAuthStore } from '@/store/authStore';

const SEATS = [
  { id: 's1', name: 'Seat 1', zone_id: 'z1', status: 'AVAILABLE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's2', name: 'Seat 2', zone_id: 'z1', status: 'ONLINE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's3', name: 'Seat 3', zone_id: 'z1', status: 'IN_USE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's4', name: 'Seat 4', zone_id: 'z1', status: 'MAINTENANCE', updated_at: '2026-01-01T00:00:00Z' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useAvailableSeats', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('fetches and filters to AVAILABLE and ONLINE seats only', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const { result } = renderHook(() => useAvailableSeats(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.length).toBe(2);
    expect(result.current.data?.every(s => s.status === 'AVAILABLE' || s.status === 'ONLINE')).toBe(true);
  });
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/seats.test.tsx`
Expected: FAIL - `useAvailableSeats` not exported

- [ ] **Step 7: Implement `useAvailableSeats` hook in `seats.ts`**

```typescript
// Add after useSeat hook (around line 144)
const AVAILABLE_STATUSES = ['AVAILABLE', 'ONLINE'] as const;

export function useAvailableSeats() {
  return useQuery({
    queryKey: ['seats', 'available'],
    queryFn: async () => {
      const all = await fetchSeats();
      return all.filter((s) => AVAILABLE_STATUSES.includes(s.status as typeof AVAILABLE_STATUSES[number]));
    },
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/seats.test.tsx`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api/members.ts frontend/src/api/seats.ts frontend/src/api/members.test.tsx frontend/src/api/seats.test.tsx
git commit -m "feat(api): add useActiveMembers and useAvailableSeats hooks for event registration"
```

---

### Task 2: Rewrite RegisterParticipantModal with member/walk-in toggle and seat assignment

**Files:**
- Modify: `frontend/src/components/events/RegisterParticipantModal.tsx` (full rewrite)
- Test: `frontend/src/components/events/RegisterParticipantModal.test.tsx` (new)

**Interfaces:**
- Consumes: `useRegisterParticipant` hook, `useActiveMembers` hook, `useAvailableSeats` hook, `toastStore`
- Produces: Modal with mode toggle, member dropdown + wallet preview, walk-in name input, seat dropdown (optional), register button

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/src/components/events/RegisterParticipantModal.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { RegisterParticipantModal } from './RegisterParticipantModal';
import { useAuthStore } from '@/store/authStore';
import { useRegisterParticipant } from '@/api/events';
import { useActiveMembers } from '@/api/members';
import { useAvailableSeats } from '@/api/seats';
import { toast } from '@/store/toastStore';

const MEMBERS = [
  { id: 'm1', name: 'Alice', phone: '9800000001', wallet_balance_paise: 5000, tier: 'BRONZE', is_active: true },
  { id: 'm2', name: 'Bob', phone: '9800000002', wallet_balance_paise: 3000, tier: 'SILVER', is_active: true },
];

const SEATS = [
  { id: 's1', name: 'Seat 1', zone_id: 'z1', status: 'AVAILABLE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's2', name: 'Seat 2', zone_id: 'z1', status: 'ONLINE', updated_at: '2026-01-01T00:00:00Z' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('RegisterParticipantModal', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'tok', staff: { id: 's1', name: 'A', role: 'ADMIN', is_active: true } });
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      return new Response(JSON.stringify({ id: 'p1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }));
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('renders member mode by default with member dropdown and wallet preview', async () => {
    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Register participant')).toBeInTheDocument());
    expect(screen.getByRole('radio', { name: /member/i })).toBeChecked();
    expect(screen.getByRole('combobox', { name: /member/i })).toBeInTheDocument();
    expect(screen.getByText(/wallet/i)).toBeInTheDocument();
  });

  it('switches to walk-in mode showing name input', async () => {
    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await userEvent.click(screen.getByRole('radio', { name: /walk.in/i }));
    expect(screen.getByRole('radio', { name: /walk.in/i })).toBeChecked();
    expect(screen.getByLabelText(/participant name/i)).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /member/i })).not.toBeInTheDocument();
  });

  it('member mode: submits member_id and seat_id', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/events/e1/register')) {
        expect(JSON.parse(opts?.body as string)).toMatchObject({ member_id: 'm1', seat_id: 's1' });
        return new Response(JSON.stringify({ id: 'e1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByRole('combobox', { name: /member/i })).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /member/i }), 'm1');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /seat/i }), 's1');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events/e1/register', expect.objectContaining({ method: 'POST' })));
  });

  it('walk-in mode: submits name and optional seat_id', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/events/e1/register')) {
        expect(JSON.parse(opts?.body as string)).toMatchObject({ name: 'Walk-in Will', seat_id: 's2' });
        return new Response(JSON.stringify({ id: 'e1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await userEvent.click(screen.getByRole('radio', { name: /walk.in/i }));
    await userEvent.type(screen.getByLabelText(/participant name/i), 'Walk-in Will');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /seat/i }), 's2');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events/e1/register', expect.objectContaining({ method: 'POST' })));
  });

  it('shows error toast on registration failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      return new Response('', { status: 500 });
    }));

    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByRole('combobox', { name: /member/i })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to register participant'));
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/events/RegisterParticipantModal.test.tsx`
Expected: FAIL - component doesn't match new design

- [ ] **Step 3: Implement rewritten RegisterParticipantModal**

```tsx
// frontend/src/components/events/RegisterParticipantModal.tsx
import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/RadioGroup';
import { toast } from '@/store/toastStore';
import { useRegisterParticipant } from '@/api/events';
import { useActiveMembers } from '@/api/members';
import { useAvailableSeats } from '@/api/seats';
import { formatPaise } from '@/lib/format';

export function RegisterParticipantModal({
  open,
  eventId,
  onClose,
  entryFeePaise = 0,
}: {
  open: boolean;
  eventId: string;
  onClose: () => void;
  entryFeePaise?: number;
}) {
  const register = useRegisterParticipant(eventId);
  const { data: members } = useActiveMembers();
  const { data: seats } = useAvailableSeats();
  const [mode, setMode] = useState<'member' | 'walkin'>('member');
  const [memberId, setMemberId] = useState('');
  const [walkinName, setWalkinName] = useState('');
  const [seatId, setSeatId] = useState('');

  const selectedMember = members?.find((m) => m.id === memberId);
  const walletPreview = selectedMember
    ? selectedMember.wallet_balance_paise - entryFeePaise
    : null;

  async function handleSubmit() {
    try {
      if (mode === 'member') {
        if (!memberId) {
          toast.error('Please select a member');
          return;
        }
        await register.mutateAsync({ member_id: memberId, seat_id: seatId || undefined });
      } else {
        if (!walkinName.trim()) {
          toast.error('Please enter a name');
          return;
        }
        await register.mutateAsync({ name: walkinName.trim(), seat_id: seatId || undefined });
      }
      toast.success('Participant registered');
      onClose();
      setMemberId('');
      setWalkinName('');
      setSeatId('');
      setMode('member');
    } catch {
      toast.error('Failed to register participant');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Register participant"
      footer={
        <Button onClick={handleSubmit} loading={register.isPending}>
          Register
        </Button>
      }
    >
      <div className="space-y-4">
        <RadioGroup value={mode} onValueChange={setMode} className="flex gap-4">
          <label className="flex items-center gap-2">
            <RadioGroupItem value="member" className="h-4 w-4" />
            <span>Member</span>
          </label>
          <label className="flex items-center gap-2">
            <RadioGroupItem value="walkin" className="h-4 w-4" />
            <span>Walk-in</span>
          </label>
        </RadioGroup>

        {mode === 'member' && (
          <div className="space-y-3">
            <Select
              label="Member"
              value={memberId}
              onValueChange={setMemberId}
              placeholder="Select member"
              options={members?.map((m) => ({ value: m.id, label: `${m.name} (${m.phone})` })) ?? []}
              required
            />
            {entryFeePaise > 0 && selectedMember && (
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Wallet balance: <strong>{formatPaise(selectedMember.wallet_balance_paise)}</strong></p>
                <p>Entry fee: <strong>{formatPaise(entryFeePaise)}</strong></p>
                <p className={walletPreview !== null && walletPreview < 0 ? 'text-destructive' : ''}>
                  After registration: <strong>{formatPaise(Math.max(0, walletPreview))}</strong>
                </p>
              </div>
            )}
          </div>
        )}

        {mode === 'walkin' && (
          <Input
            label="Participant name"
            value={walkinName}
            onChange={(e) => setWalkinName(e.target.value)}
            autoFocus
            required
            placeholder="Enter name"
          />
        )}

        {(seats?.length ?? 0) > 0 && (
          <Select
            label="Seat (optional)"
            value={seatId}
            onValueChange={setSeatId}
            placeholder="Assign seat"
            options={seats.map((s) => ({ value: s.id, label: `${s.name} (${s.status})` }))}
          />
        )}
      </div>
    </Modal>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/events/RegisterParticipantModal.test.tsx`
Expected: PASS

- [ ] **Step 5: Update EventDetail to pass entryFeePaise to modal**

```tsx
// frontend/src/components/events/EventDetail.tsx - modify line 48-52
<RegisterParticipantModal
  open={isRegisterOpen}
  eventId={eventId}
  entryFeePaise={summary.event.entry_fee_paise}
  onClose={() => setIsRegisterOpen(false)}
/>
```

- [ ] **Step 6: Run Events.test.tsx to ensure integration works**

Run: `cd frontend && npx vitest run src/pages/Events.test.tsx`
Expected: PASS (update test if needed for new modal)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/events/RegisterParticipantModal.tsx frontend/src/components/events/RegisterParticipantModal.test.tsx frontend/src/components/events/EventDetail.tsx
git commit -m "feat(events): rewrite RegisterParticipantModal with member/walk-in toggle and seat assignment"
```

---

### Task 3: Create EventsWidget component for Dashboard

**Files:**
- Create: `frontend/src/components/events/EventsWidget.tsx`
- Create: `frontend/src/components/events/EventsWidget.test.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx` (import and render)

**Interfaces:**
- Consumes: `useEvents` hook (existing), `formatPaise` utility, `formatDateTime` utility
- Produces: Widget showing upcoming events (status=UPCOMING), sorted by event_date, with "View All" link to `/events`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/components/events/EventsWidget.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { EventsWidget } from './EventsWidget';
import { useAuthStore } from '@/store/authStore';
import { useEvents } from '@/api/events';

const EVENTS = [
  { id: 'e1', name: 'FIFA Cup', game_title: 'FIFA 24', event_date: '2026-08-15T18:00:00Z', entry_fee_paise: 5000, prize_pool_paise: 20000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
  { id: 'e2', name: 'Tekken Tournament', game_title: 'Tekken 8', event_date: '2026-08-20T19:00:00Z', entry_fee_paise: 3000, prize_pool_paise: 10000, bracket_type: 'DOUBLE_ELIMINATION', status: 'UPCOMING' },
  { id: 'e3', name: 'Past Event', game_title: 'Street Fighter', event_date: '2026-07-01T18:00:00Z', entry_fee_paise: 2000, prize_pool_paise: 5000, bracket_type: 'SINGLE_ELIMINATION', status: 'COMPLETED' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('EventsWidget', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('renders upcoming events sorted by date', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Upcoming Events')).toBeInTheDocument());
    expect(screen.getByText('FIFA Cup')).toBeInTheDocument();
    expect(screen.getByText('Tekken Tournament')).toBeInTheDocument();
    expect(screen.queryByText('Past Event')).not.toBeInTheDocument();
    // FIFA Cup should appear first (earlier date)
    const fifaIndex = screen.getByText('FIFA Cup').parentElement?.textContent?.indexOf('FIFA Cup') ?? 0;
    const tekkenIndex = screen.getByText('Tekken Tournament').parentElement?.textContent?.indexOf('Tekken Tournament') ?? 0;
    expect(fifaIndex).toBeLessThan(tekkenIndex);
  });

  it('shows entry fee, prize pool, and participant count per event', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
    expect(screen.getByText('₹50.00')).toBeInTheDocument(); // entry fee
    expect(screen.getByText('₹200.00')).toBeInTheDocument(); // prize pool
  });

  it('shows empty state when no upcoming events', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify([EVENTS[2]]), { status: 200, headers: { 'Content-Type': 'application/json' } }))); // only completed
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText(/no upcoming events/i)).toBeInTheDocument());
  });

  it('View All button navigates to /events', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByRole('link', { name: /view all/i })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('link', { name: /view all/i }));
    // Note: navigation test depends on router setup; verify link href
    expect(screen.getByRole('link', { name: /view all/i })).toHaveAttribute('href', '/events');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/events/EventsWidget.test.tsx`
Expected: FAIL - component doesn't exist

- [ ] **Step 3: Implement EventsWidget component**

```tsx
// frontend/src/components/events/EventsWidget.tsx
import { Link } from 'react-router-dom';
import { Calendar, Trophy, Users, ArrowRight } from 'lucide-react';
import { useEvents } from '@/api/events';
import { formatPaise, formatDateTime } from '@/lib/format';

export function EventsWidget() {
  const { data: events, isLoading } = useEvents();
  const upcoming = events
    ?.filter((e) => e.status === 'UPCOMING')
    .sort((a, b) => new Date(a.event_date).getTime() - new Date(b.event_date).getTime());

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-medium text-foreground">Upcoming Events</h3>
        </div>
        <div className="h-8 w-full animate-pulse rounded bg-muted" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-medium text-foreground">Upcoming Events</h3>
        <Link to="/events" className="text-sm text-primary hover:underline flex items-center gap-1">
          View All <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {upcoming && upcoming.length > 0 ? (
        <div className="space-y-3">
          {upcoming.map((event) => (
            <div key={event.id} className="rounded-md border border-border p-3 hover:bg-muted/50 transition-colors">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <span className="text-lg">🎮</span>
                    <span className="truncate">{event.name}</span>
                    <span className="text-muted-foreground whitespace-nowrap">{event.game_title}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDateTime(event.event_date)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Trophy className="h-3 w-3" />
                      {formatPaise(event.prize_pool_paise)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      ₹{event.entry_fee_paise / 100}
                    </span>
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-success/10 text-success">
                      {event.status}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground text-center py-4">
          No upcoming events. Create one on the <Link to="/events" className="text-primary hover:underline">Events page</Link>.
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/events/EventsWidget.test.tsx`
Expected: PASS

- [ ] **Step 5: Update Dashboard.tsx to include EventsWidget**

```tsx
// frontend/src/pages/Dashboard.tsx - add import and render after header
import { EventsWidget } from '@/components/events/EventsWidget';

// In the main section, after <UnprintedInvoices /> and before <SeatGrid />
<main className="mx-auto w-full max-w-7xl space-y-6 p-6">
  <UnprintedInvoices />
  <EventsWidget />
  <SeatGrid />
</main>
```

- [ ] **Step 6: Run Dashboard.test.tsx to verify integration**

Run: `cd frontend && npx vitest run src/pages/Dashboard.test.tsx`
Expected: PASS (add test for EventsWidget if needed)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/events/EventsWidget.tsx frontend/src/components/events/EventsWidget.test.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat(events): add EventsWidget to Dashboard showing upcoming tournaments"
```

---

### Task 4: Extend frontend test coverage for new registration flows and widget

**Files:**
- Modify: `frontend/src/pages/Events.test.tsx` (add tests for member/walk-in registration, seat assignment)
- Modify: `frontend/src/pages/Dashboard.test.tsx` (add test for EventsWidget rendering)

**Interfaces:**
- Consumes: existing test infrastructure, new `RegisterParticipantModal` tests
- Produces: comprehensive test coverage for J.2 and J.4 acceptance criteria

- [ ] **Step 1: Extend Events.test.tsx with new registration flow tests**

```tsx
// Add to frontend/src/pages/Events.test.tsx after existing tests

describe('EventsPage - Registration flows', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'tok', staff: { id: 's1', name: 'A', role: 'ADMIN', is_active: true } });
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('member registration: shows wallet preview and deducts entry fee', async () => {
    const MEMBERS = [{ id: 'm1', name: 'Alice', phone: '9800000001', wallet_balance_paise: 10000, tier: 'BRONZE', is_active: true }];
    const SEATS = [{ id: 's1', name: 'Seat 1', zone_id: 'z1', status: 'AVAILABLE', updated_at: '2026-01-01T00:00:00Z' }];
    const SUMMARY = {
      event: { id: 'e1', name: 'Test Cup', game_title: 'Game', event_date: '2026-08-01T10:00:00Z', entry_fee_paise: 3000, prize_pool_paise: 10000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
      participant_count: 0, participants: [], match_count: 0, completed_match_count: 0,
      prize_pool_paise: 10000, entry_fee_paise: 3000, entry_fee_revenue_paise: 0,
      champion_participant_id: null, is_complete: false, matches: [],
    };

    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/summary')) return new Response(JSON.stringify(SUMMARY), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/events/e1/register') && opts?.method === 'POST') {
        const body = JSON.parse(opts.body as string);
        expect(body.member_id).toBe('m1');
        expect(body.seat_id).toBe('s1');
        return new Response(JSON.stringify({ id: 'e1', ...SUMMARY.event }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response(JSON.stringify([SUMMARY.event]), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<EventsPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Test Cup')).toBeInTheDocument());
    await userEvent.click(screen.getByLabelText(/open event test cup/i));
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Participants' })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: 'Participants' }));
    await userEvent.click(screen.getByRole('button', { name: /register participant/i }));
    await waitFor(() => expect(screen.getByRole('radio', { name: /member/i })).toBeChecked());
    expect(screen.getByText(/wallet balance/i)).toBeInTheDocument();
    expect(screen.getByText('₹100.00')).toBeInTheDocument(); // wallet
    expect(screen.getByText('₹30.00')).toBeInTheDocument(); // entry fee
    expect(screen.getByText('₹70.00')).toBeInTheDocument(); // after
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /member/i }), 'm1');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /seat/i }), 's1');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events/e1/register', expect.objectContaining({ method: 'POST' })));
  });

  it('walk-in registration: requires name, seat optional', async () => {
    const SEATS = [{ id: 's1', name: 'Seat 1', zone_id: 'z1', status: 'AVAILABLE', updated_at: '2026-01-01T00:00:00Z' }];
    const SUMMARY = {
      event: { id: 'e1', name: 'Test Cup', game_title: 'Game', event_date: '2026-08-01T10:00:00Z', entry_fee_paise: 0, prize_pool_paise: 10000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
      participant_count: 0, participants: [], match_count: 0, completed_match_count: 0,
      prize_pool_paise: 10000, entry_fee_paise: 0, entry_fee_revenue_paise: 0,
      champion_participant_id: null, is_complete: false, matches: [],
    };

    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/summary')) return new Response(JSON.stringify(SUMMARY), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/events/e1/register') && opts?.method === 'POST') {
        const body = JSON.parse(opts.body as string);
        expect(body.name).toBe('Walk-in Will');
        expect(body.seat_id).toBe('s1');
        expect(body.member_id).toBeUndefined();
        return new Response(JSON.stringify({ id: 'e1', ...SUMMARY.event }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response(JSON.stringify([SUMMARY.event]), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<EventsPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Test Cup')).toBeInTheDocument());
    await userEvent.click(screen.getByLabelText(/open event test cup/i));
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Participants' })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: 'Participants' }));
    await userEvent.click(screen.getByRole('button', { name: /register participant/i }));
    await userEvent.click(screen.getByRole('radio', { name: /walk.in/i }));
    expect(screen.getByLabelText(/participant name/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/participant name/i), 'Walk-in Will');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /seat/i }), 's1');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events/e1/register', expect.objectContaining({ method: 'POST' })));
  });
});
```

- [ ] **Step 2: Run Events.test.tsx to verify new tests pass**

Run: `cd frontend && npx vitest run src/pages/Events.test.tsx`
Expected: PASS (8 tests total)

- [ ] **Step 3: Extend Dashboard.test.tsx for EventsWidget**

```tsx
// Add to frontend/src/pages/Dashboard.test.tsx

describe('DashboardPage - EventsWidget', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'tok', staff: { id: 's1', name: 'A', role: 'ADMIN', is_active: true } });
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('renders EventsWidget with upcoming events', async () => {
    const EVENTS = [
      { id: 'e1', name: 'FIFA Cup', game_title: 'FIFA 24', event_date: '2026-08-15T18:00:00Z', entry_fee_paise: 5000, prize_pool_paise: 20000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
      { id: 'e2', name: 'Past Event', game_title: 'Game', event_date: '2026-07-01T18:00:00Z', entry_fee_paise: 2000, prize_pool_paise: 5000, bracket_type: 'SINGLE_ELIMINATION', status: 'COMPLETED' },
    ];

    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));

    render(<DashboardPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Upcoming Events')).toBeInTheDocument());
    expect(screen.getByText('FIFA Cup')).toBeInTheDocument();
    expect(screen.queryByText('Past Event')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view all/i })).toHaveAttribute('href', '/events');
  });
});
```

- [ ] **Step 4: Run Dashboard.test.tsx to verify**

Run: `cd frontend && npx vitest run src/pages/Dashboard.test.tsx`
Expected: PASS

- [ ] **Step 5: Run full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests pass (354+)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Events.test.tsx frontend/src/pages/Dashboard.test.tsx
git commit -m "test(events): extend coverage for member/walk-in registration and EventsWidget"
```

---

### Task 5: Full verification and acceptance criteria check

**Files:**
- No new files — run existing test suites

**Interfaces:**
- Verifies all J.1–J.4 acceptance criteria from TODO.md

- [ ] **Step 1: Run backend event tests (J.1, J.3)**

Run: `cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_events.py backend/tests/test_events_router.py backend/tests/test_event_service.py backend/tests/test_events_e2e_smoke.py -v`
Expected: 25 tests PASS

- [ ] **Step 2: Run frontend event tests (J.2, J.4)**

Run: `cd frontend && npx vitest run src/pages/Events.test.tsx src/pages/Dashboard.test.tsx src/components/events/RegisterParticipantModal.test.tsx src/components/events/EventsWidget.test.tsx src/api/members.test.tsx src/api/seats.test.tsx`
Expected: All tests PASS

- [ ] **Step 3: Run full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: 354+ tests PASS

- [ ] **Step 4: Run full backend test suite**

Run: `cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/ -v --tb=short`
Expected: 1000+ tests PASS

- [ ] **Step 5: Run linters**

Run: `cd "E:\Ongoing Projects\Arcade" && make lint`
Expected: ruff + mypy strict + ESLint all PASS

- [ ] **Step 6: Verify acceptance criteria mapping**

| TODO Item | Verified By |
|-----------|-------------|
| J.1 Event creation | Backend tests (test_events.py::test_create_event, test_events_router.py::test_create_and_list) |
| J.2 Participant registration + seats | Frontend tests (Events.test.tsx new tests) + backend test_events_e2e_smoke.py |
| J.3 Brackets | Backend tests (test_events.py::test_single_elimination_advancement, test_double_elimination_advancement) |
| J.4 Event billing + dashboard | Frontend tests (Events.test.tsx wallet deduction, Dashboard.test.tsx EventsWidget) |

- [ ] **Step 7: Final commit if all green**

```bash
git add -A
git commit -m "feat(events): complete Section J Events & Tournaments frontend — registration flows + Dashboard widget"
```
