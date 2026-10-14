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

// Accents are ignored so "sueter" finds "suéter".
function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function matchesSearch(garment: Garment, search: string): boolean {
  if (!search) return true;
  const text = `${garment.name ?? ''} ${garment.color ?? ''} ${garment.brand ?? ''}`;
  return normalize(text).includes(normalize(search));
}

export type ClosetColumns = 3 | 4;
export type ClosetSort = 'recent' | 'most_worn' | 'least_worn';

export const SORT_OPTIONS: { value: ClosetSort; label: string }[] = [
  { value: 'recent', label: 'Recientes' },
  { value: 'most_worn', label: 'Más usadas' },
  { value: 'least_worn', label: 'Menos usadas' },
];

// How the closet grid is laid out and ordered; kept on the phone between launches.
export const useClosetColumns = create<{ columns: ClosetColumns; sort: ClosetSort }>()(
  persist(() => ({ columns: 3 as ClosetColumns, sort: 'recent' as ClosetSort }), {
    name: 'closet-columns',
    storage: createJSONStorage(() => AsyncStorage),
  })
);
