import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Member, Package, MemberPackageEntitlement, WalletTransaction } from '@/types/members';
import type { SessionResponse } from '@/types/session';
import type { PaymentMethod } from '@/types/invoice';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export async function listMembers(
  params: { q?: string; limit?: number; offset?: number },
  token: string | null,
): Promise<Member[]> {
  const qs = new URLSearchParams({
    q: params.q ?? '',
    limit: String(params.limit ?? 50),
    offset: String(params.offset ?? 0),
  });
  const res = await fetch(`${API_BASE}/members?${qs}`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load members: ${res.status}`);
  return (await res.json()) as Member[];
}

// Alias kept for MemberSearch (Task 16)
export const searchMembers = (q: string, token: string | null) => listMembers({ q }, token);

export async function createMember(
  p: { name: string; phone: string },
  token: string | null,
): Promise<Member> {
  const res = await fetch(`${API_BASE}/members`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(p),
  });
  if (!res.ok) throw new Error(`Failed to create member: ${res.status}`);
  return (await res.json()) as Member;
}

export async function topupWallet(
  id: string,
  p: { amount_paise: number; payment_method: PaymentMethod },
  token: string | null,
): Promise<Member> {
  const res = await fetch(`${API_BASE}/members/${id}/topup`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(p),
  });
  if (!res.ok) throw new Error(`Failed to top up wallet: ${res.status}`);
  return (await res.json()) as Member;
}

export async function listPackages(token: string | null): Promise<Package[]> {
  const res = await fetch(`${API_BASE}/packages`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load packages: ${res.status}`);
  return (await res.json()) as Package[];
}

export async function purchasePackage(
  id: string,
  p: { package_id: string; payment_method: PaymentMethod },
  token: string | null,
): Promise<MemberPackageEntitlement> {
  const res = await fetch(`${API_BASE}/packages/members/${id}/packages`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(p),
  });
  if (!res.ok) throw new Error(`Failed to purchase package: ${res.status}`);
  return (await res.json()) as MemberPackageEntitlement;
}

export async function listMemberSessions(
  id: string,
  token: string | null,
): Promise<SessionResponse[]> {
  const res = await fetch(`${API_BASE}/members/${id}/sessions`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to load sessions: ${res.status}`);
  return (await res.json()) as SessionResponse[];
}

export async function listWalletTransactions(
  id: string,
  p: { limit?: number; offset?: number },
  token: string | null,
): Promise<WalletTransaction[]> {
  const qs = new URLSearchParams({
    limit: String(p.limit ?? 50),
    offset: String(p.offset ?? 0),
  });
  const res = await fetch(`${API_BASE}/members/${id}/transactions?${qs}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to load wallet transactions: ${res.status}`);
  return (await res.json()) as WalletTransaction[];
}

// --- React Query hooks ---

export function useMembers(q = '') {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['members', q],
    queryFn: () => listMembers({ q }, token),
    staleTime: 30_000,
  });
}

export function useCreateMember() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { name: string; phone: string }) => createMember(p, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members'] }),
  });
}

export function useTopupWallet() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; amount_paise: number; payment_method: PaymentMethod }) =>
      topupWallet(vars.id, vars, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members'] }),
  });
}

export function usePackages() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['packages'],
    queryFn: () => listPackages(token),
    staleTime: 60_000,
  });
}

export function usePurchasePackage() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; package_id: string; payment_method: PaymentMethod }) =>
      purchasePackage(vars.id, { package_id: vars.package_id, payment_method: vars.payment_method }, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] });
      qc.invalidateQueries({ queryKey: ['packages'] });
    },
  });
}

export function useMemberSessions(id: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['memberSessions', id],
    queryFn: () => listMemberSessions(id, token),
    enabled: !!id && !!token,
    staleTime: 30_000,
  });
}

export function useWalletTransactions(
  id: string,
  params: { limit?: number; offset?: number } = {},
) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['walletTransactions', id, params.limit, params.offset],
    queryFn: () => listWalletTransactions(id, params, token),
    enabled: !!id && !!token,
    staleTime: 30_000,
  });
}
