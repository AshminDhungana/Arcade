import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type {
  EventResponse, EventSummaryResponse, EventCreate,
  EventRegisterRequest, EventMatchResultRequest,
} from '@/types/events';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export async function fetchEvents(token: string | null): Promise<EventResponse[]> {
  const res = await fetch(`${API_BASE}/events`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load events: ${res.status} ${res.statusText}`);
  return (await res.json()) as EventResponse[];
}

export function useEvents() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['events'],
    queryFn: () => fetchEvents(token),
    enabled: !!token,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export async function fetchEventSummary(eventId: string, token: string | null): Promise<EventSummaryResponse> {
  const res = await fetch(`${API_BASE}/events/${eventId}/summary`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load event: ${res.status} ${res.statusText}`);
  return (await res.json()) as EventSummaryResponse;
}

export function useEventSummary(eventId: string | null) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['events', 'summary', eventId],
    queryFn: () => fetchEventSummary(eventId!, token),
    enabled: !!token && !!eventId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export async function createEvent(p: EventCreate, token: string | null): Promise<EventResponse> {
  const res = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(p),
  });
  if (!res.ok) throw new Error(`Failed to create event: ${res.status}`);
  return (await res.json()) as EventResponse;
}

export function useCreateEvent() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: EventCreate) => createEvent(p, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['events'] }),
  });
}

export async function registerParticipant(eventId: string, p: EventRegisterRequest, token: string | null): Promise<EventResponse> {
  const res = await fetch(`${API_BASE}/events/${eventId}/register`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(p),
  });
  if (!res.ok) throw new Error(`Failed to register participant: ${res.status}`);
  return (await res.json()) as EventResponse;
}

export function useRegisterParticipant(eventId: string) {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: EventRegisterRequest) => registerParticipant(eventId, p, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['events', 'summary', eventId] }),
  });
}

export async function recordMatchResult(eventId: string, p: EventMatchResultRequest, token: string | null): Promise<unknown> {
  const res = await fetch(`${API_BASE}/events/${eventId}/match`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(p),
  });
  if (!res.ok) throw new Error(`Failed to record result: ${res.status}`);
  return res.json();
}

export function useRecordMatchResult(eventId: string) {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: EventMatchResultRequest) => recordMatchResult(eventId, p, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['events', 'summary', eventId] }),
  });
}
