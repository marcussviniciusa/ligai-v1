import { create } from 'zustand';

interface CallStore {
  selectedCallId: string | null;
  setSelectedCallId: (id: string | null) => void;
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

export const useCallStore = create<CallStore>((set) => ({
  selectedCallId: null,
  setSelectedCallId: (id) => set({ selectedCallId: id }),
  notifications: [],
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { ...notification, id: Date.now().toString() },
      ],
    })),
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}));
