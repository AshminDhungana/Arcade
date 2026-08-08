import { create } from 'zustand';
import { playStaffAlertChime } from '@/lib/chime';

export interface StaffAlert {
  id: string;
  type: string;
  seat_id: string;
  message: string;
  timestamp: string;
}

interface AlertStore {
  alerts: StaffAlert[];
  push: (alert: Omit<StaffAlert, 'id'>) => void;
  dismiss: () => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  push: (alert) => {
    playStaffAlertChime();
    set((state) => ({
      alerts: [...state.alerts, { ...alert, id: crypto.randomUUID() }],
    }));
  },
  dismiss: () => set((state) => ({ alerts: state.alerts.slice(1) })),
}));
