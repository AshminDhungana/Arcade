import { create } from 'zustand';

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  persistent?: boolean;
  onClick?: () => void;
  dismissLabel?: string;
  createdAt: number;
}

interface ToastStore {
  toasts: Toast[];
  push: (toast: Omit<Toast, 'id' | 'createdAt'>) => string;
  dismiss: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  push: (toast) => {
    const id = crypto.randomUUID();
    const newToast: Toast = {
      ...toast,
      id,
      createdAt: Date.now(),
    };
    set((state) => ({ toasts: [...state.toasts, newToast] }));

    if (!toast.persistent) {
      setTimeout(() => {
        get().dismiss(id);
      }, 4000);
    }

    return id;
  },
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

export const toast = {
  success: (message: string, options?: { persistent?: boolean; onClick?: () => void; dismissLabel?: string }) =>
    useToastStore.getState().push({ message, type: 'success', ...options }),
  error: (message: string, options?: { persistent?: boolean; onClick?: () => void; dismissLabel?: string }) =>
    useToastStore.getState().push({ message, type: 'error', ...options }),
  info: (message: string, options?: { persistent?: boolean; onClick?: () => void; dismissLabel?: string }) =>
    useToastStore.getState().push({ message, type: 'info', ...options }),
  warning: (message: string, options?: { persistent?: boolean; onClick?: () => void; dismissLabel?: string }) =>
    useToastStore.getState().push({ message, type: 'warning', ...options }),
};