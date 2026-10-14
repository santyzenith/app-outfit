import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { Garment } from '@/lib/garments';

type ClosetFilters = {
  warmth: Garment['warmth'];
  formality: Garment['formality'];
  color: string | null;
};

const NONE: ClosetFilters = { warmth: null, formality: null, color: null };

export const useClosetFilters = create<ClosetFilters>(() => NONE);

export function clearClosetFilters(): void {
  useClosetFilters.setState(NONE);
}

export function activeFilterCount(filters: ClosetFilters): number {
  return Object.values(filters).filter((value) => value !== null).length;
}

// "azul marino" and "azul claro" both count as "Azul".
export function colorFamily(color: string | null): string | null {
  const first = color?.trim().split(/\s+/)[0];
  return first ? first.charAt(0).toUpperCase() + first.slice(1).toLowerCase() : null;
}

export function matchesFilters(garment: Garment, filters: ClosetFilters): boolean {
  return (
    (!filters.warmth || garment.warmth === filters.warmth) &&
    (!filters.formality || garment.formality === filters.formality) &&
    (!filters.color || colorFamily(garment.color) === filters.color)
  );
}

export type ClosetColumns = 3 | 4;

// How dense the closet grid is; kept on the phone between launches.
export const useClosetColumns = create<{ columns: ClosetColumns }>()(
  persist(() => ({ columns: 3 as ClosetColumns }), {
    name: 'closet-columns',
    storage: createJSONStorage(() => AsyncStorage),
  })
);
