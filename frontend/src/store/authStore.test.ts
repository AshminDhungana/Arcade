import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore, Staff } from './authStore';

describe('AuthStore', () => {
  beforeEach(() => {
    // Reset Zustand state before each test
    useAuthStore.setState({
      accessToken: null,
      staff: null,
      isAuthenticated: false,
    });
  });

  it('has no token initially', () => {
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.staff).toBeNull();
  });

  it('stores token and staff on login', () => {
    const staff: Staff = { id: 'STAFF-001', name: 'Alice', role: 'ADMIN', is_active: true };
    useAuthStore.getState().login('mock-token', staff);
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('mock-token');
    expect(state.staff).toEqual(staff);
    expect(state.isAuthenticated).toBe(true);
  });

  it('clears state on logout', () => {
    const staff: Staff = { id: 'STAFF-001', name: 'Alice', role: 'ADMIN', is_active: true };
    useAuthStore.getState().login('mock-token', staff);
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.staff).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('clears state on clear', () => {
    const staff: Staff = { id: 'STAFF-001', name: 'Alice', role: 'ADMIN', is_active: true };
    useAuthStore.getState().login('mock-token', staff);
    useAuthStore.getState().clear();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.staff).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});
