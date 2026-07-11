import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  Zone,
  DeviceType,
  PeakSchedule,
  Staff,
  MenuItem,
} from '@/types/settings';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// Existing settings PATCH + toggle hook (Tasks 11/12) — KEEP
export async function patchSettings(
  patch: Record<string, string>,
  token: string | null,
): Promise<Record<string, string>> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Update failed: ${res.status}`);
  }
  return (await res.json()) as Record<string, string>;
}

export function useToggleFlag() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { key: string; value: boolean }) =>
      patchSettings({ [vars.key]: vars.value ? 'true' : 'false' }, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['featureFlags'] });
    },
  });
}

// ---------- Settings (read) ----------
export async function getSettings(token: string | null): Promise<Record<string, string>> {
  const res = await fetch(`${API_BASE}/settings`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load settings: ${res.status}`);
  return (await res.json()) as Record<string, string>;
}

export function useSettings() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => getSettings(token),
    staleTime: 30_000,
  });
}

// Printer config is stored as scalar settings keys (Task 24/32). The brief's
// JSON-string shape was replaced with the actual backend keys.
export interface PrinterConfig {
  type: 'usb' | 'network' | '';
  vendor: string;
  product: string;
}

export function parsePrinterConfig(settings: Record<string, string>): PrinterConfig {
  return {
    type: (settings['printer_type'] ?? '') as PrinterConfig['type'],
    vendor: settings['printer_usb_vendor'] ?? '',
    product: settings['printer_usb_product'] ?? '',
  };
}

// ---------- Zones ----------
export async function listZones(token: string | null): Promise<Zone[]> {
  const res = await fetch(`${API_BASE}/zones`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load zones: ${res.status}`);
  return (await res.json()) as Zone[];
}

export async function createZone(
  z: Omit<Zone, 'id'>,
  token: string | null,
): Promise<Zone> {
  const res = await fetch(`${API_BASE}/zones`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(z),
  });
  if (!res.ok) throw new Error(`Failed to create zone: ${res.status}`);
  return (await res.json()) as Zone;
}

export async function updateZone(
  id: string,
  z: Partial<Omit<Zone, 'id'>>,
  token: string | null,
): Promise<Zone> {
  const res = await fetch(`${API_BASE}/zones/${id}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(z),
  });
  if (!res.ok) throw new Error(`Failed to update zone: ${res.status}`);
  return (await res.json()) as Zone;
}

export async function deleteZone(id: string, token: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/zones/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to delete zone: ${res.status}`);
}

// ---------- Device types ----------
export async function listDeviceTypes(token: string | null): Promise<DeviceType[]> {
  const res = await fetch(`${API_BASE}/device-types`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load device types: ${res.status}`);
  return (await res.json()) as DeviceType[];
}

export async function createDeviceType(
  d: Omit<DeviceType, 'id'>,
  token: string | null,
): Promise<DeviceType> {
  const res = await fetch(`${API_BASE}/device-types`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(d),
  });
  if (!res.ok) throw new Error(`Failed to create device type: ${res.status}`);
  return (await res.json()) as DeviceType;
}

export async function updateDeviceType(
  id: string,
  d: Partial<Omit<DeviceType, 'id'>>,
  token: string | null,
): Promise<DeviceType> {
  const res = await fetch(`${API_BASE}/device-types/${id}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(d),
  });
  if (!res.ok) throw new Error(`Failed to update device type: ${res.status}`);
  return (await res.json()) as DeviceType;
}

export async function deleteDeviceType(
  id: string,
  token: string | null,
): Promise<void> {
  const res = await fetch(`${API_BASE}/device-types/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to delete device type: ${res.status}`);
}

// ---------- Schedules ----------
export async function listSchedules(token: string | null): Promise<PeakSchedule[]> {
  const res = await fetch(`${API_BASE}/schedules`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load schedules: ${res.status}`);
  return (await res.json()) as PeakSchedule[];
}

export async function createSchedule(
  s: Omit<PeakSchedule, 'id'>,
  token: string | null,
): Promise<PeakSchedule> {
  const res = await fetch(`${API_BASE}/schedules`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(s),
  });
  if (!res.ok) throw new Error(`Failed to create schedule: ${res.status}`);
  return (await res.json()) as PeakSchedule;
}

export async function updateSchedule(
  id: string,
  s: Partial<Omit<PeakSchedule, 'id'>>,
  token: string | null,
): Promise<PeakSchedule> {
  const res = await fetch(`${API_BASE}/schedules/${id}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(s),
  });
  if (!res.ok) throw new Error(`Failed to update schedule: ${res.status}`);
  return (await res.json()) as PeakSchedule;
}

export async function deleteSchedule(id: string, token: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/schedules/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to delete schedule: ${res.status}`);
}

// ---------- Staff ----------
export async function listStaff(token: string | null): Promise<Staff[]> {
  const res = await fetch(`${API_BASE}/staff`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load staff: ${res.status}`);
  return (await res.json()) as Staff[];
}

export async function createStaff(
  s: { name: string; role: Staff['role']; pin: string; is_active?: boolean },
  token: string | null,
): Promise<Staff> {
  const res = await fetch(`${API_BASE}/staff`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(s),
  });
  if (!res.ok) throw new Error(`Failed to create staff: ${res.status}`);
  return (await res.json()) as Staff;
}

export async function deactivateStaff(
  id: string,
  token: string | null,
): Promise<Staff> {
  const res = await fetch(`${API_BASE}/staff/${id}/deactivate`, {
    method: 'PATCH',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to deactivate staff: ${res.status}`);
  return (await res.json()) as Staff;
}

export async function reactivateStaff(
  id: string,
  token: string | null,
): Promise<Staff> {
  const res = await fetch(`${API_BASE}/staff/${id}/reactivate`, {
    method: 'PATCH',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to reactivate staff: ${res.status}`);
  return (await res.json()) as Staff;
}

// ---------- Menu items ----------
export async function listMenuItems(token: string | null): Promise<MenuItem[]> {
  const res = await fetch(`${API_BASE}/menu-items`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load menu items: ${res.status}`);
  return (await res.json()) as MenuItem[];
}

export async function createMenuItem(
  m: Omit<MenuItem, 'id'>,
  token: string | null,
): Promise<MenuItem> {
  const res = await fetch(`${API_BASE}/menu-items`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(m),
  });
  if (!res.ok) throw new Error(`Failed to create menu item: ${res.status}`);
  return (await res.json()) as MenuItem;
}

export async function updateMenuItem(
  id: string,
  m: Partial<Omit<MenuItem, 'id'>>,
  token: string | null,
): Promise<MenuItem> {
  const res = await fetch(`${API_BASE}/menu-items/${id}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(m),
  });
  if (!res.ok) throw new Error(`Failed to update menu item: ${res.status}`);
  return (await res.json()) as MenuItem;
}

export async function deleteMenuItem(id: string, token: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/menu-items/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to delete menu item: ${res.status}`);
}

// ---------- React Query hooks ----------

// Zones
export function useZones() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['zones'],
    queryFn: () => listZones(token),
    staleTime: 60_000,
  });
}

export function useCreateZone() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (z: Omit<Zone, 'id'>) => createZone(z, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['zones'] }),
  });
}

export function useUpdateZone() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; data: Partial<Omit<Zone, 'id'>> }) =>
      updateZone(vars.id, vars.data, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['zones'] }),
  });
}

export function useDeleteZone() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteZone(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['zones'] }),
  });
}

// Device types
export function useDeviceTypes() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['deviceTypes'],
    queryFn: () => listDeviceTypes(token),
    staleTime: 60_000,
  });
}

export function useCreateDeviceType() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (d: Omit<DeviceType, 'id'>) => createDeviceType(d, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deviceTypes'] }),
  });
}

export function useUpdateDeviceType() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; data: Partial<Omit<DeviceType, 'id'>> }) =>
      updateDeviceType(vars.id, vars.data, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deviceTypes'] }),
  });
}

export function useDeleteDeviceType() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDeviceType(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deviceTypes'] }),
  });
}

// Schedules
export function useSchedules() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['schedules'],
    queryFn: () => listSchedules(token),
    staleTime: 60_000,
  });
}

export function useCreateSchedule() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (s: Omit<PeakSchedule, 'id'>) => createSchedule(s, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  });
}

export function useUpdateSchedule() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; data: Partial<Omit<PeakSchedule, 'id'>> }) =>
      updateSchedule(vars.id, vars.data, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  });
}

export function useDeleteSchedule() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSchedule(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  });
}

// Staff
export function useStaff() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['staff'],
    queryFn: () => listStaff(token),
    staleTime: 30_000,
  });
}

export function useCreateStaff() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (s: { name: string; role: Staff['role']; pin: string; is_active?: boolean }) =>
      createStaff(s, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff'] }),
  });
}

export function useDeactivateStaff() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deactivateStaff(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff'] }),
  });
}

export function useReactivateStaff() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reactivateStaff(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff'] }),
  });
}

// Menu items
export function useMenuItems() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['menuItems'],
    queryFn: () => listMenuItems(token),
    staleTime: 30_000,
  });
}

export function useCreateMenuItem() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (m: Omit<MenuItem, 'id'>) => createMenuItem(m, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['menuItems'] }),
  });
}

export function useUpdateMenuItem() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; data: Partial<Omit<MenuItem, 'id'>> }) =>
      updateMenuItem(vars.id, vars.data, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['menuItems'] }),
  });
}

export function useDeleteMenuItem() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMenuItem(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['menuItems'] }),
  });
}
