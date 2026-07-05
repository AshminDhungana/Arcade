import { create } from 'zustand';

/** Minimal staff payload from the login API (mirrors backend StaffResponse). */
export interface Staff {
  id: string;
  name: string;
  role: string;
  is_active: boolean;
}

interface AuthStore {
  accessToken: string | null;
  staff: Staff | null;
  isAuthenticated: boolean;

  /** Called after a successful login to persist token and staff info. */
  login: (token: string, staff: Staff) => void;

  /** Called on explicit logout or when a 401/403 is received. */
  logout: () => void;

  /** Reset the store to its initial state. */
  clear: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  staff: null,
  isAuthenticated: false,

  login: (token, staff) =>
    set({
      accessToken: token,
      staff,
      isAuthenticated: true,
    }),

  logout: () =>
    set({
      accessToken: null,
      staff: null,
      isAuthenticated: false,
    }),

  clear: () =>
    set({
      accessToken: null,
      staff: null,
      isAuthenticated: false,
    }),
}));
