import { create } from 'zustand';

/** Individual per-seat health snapshot (mirrors backend HealthMetricsResponse). */
export interface HealthMetrics {
  seat_id: string;
  cpu_pct: number;
  ram_pct: number;
  cpu_temp?: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  timestamp: string;
}

interface HealthStore {
  metrics: Record<string, HealthMetrics>;
  setHealth: (seatId: string, data: HealthMetrics) => void;
  getSeatHealth: (seatId: string) => HealthMetrics | undefined;
}

export const useHealthStore = create<HealthStore>((set, get) => ({
  metrics: {},
  setHealth: (seatId: string, data: HealthMetrics) =>
    set((state) => ({
      metrics: { ...state.metrics, [seatId]: data },
    })),
  getSeatHealth: (seatId: string) => get().metrics[seatId],
}));
