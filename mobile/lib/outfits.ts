import { useMutation, useQuery } from '@tanstack/react-query';
import { create } from 'zustand';

import { api } from '@/lib/api';
import { type Garment, type GarmentCategory, refreshGarments } from '@/lib/garments';
import type { Coords } from '@/lib/location';
import { queryClient } from '@/lib/query';

export type Occasion = 'casual' | 'work' | 'night_out' | 'formal';

export type Outfit = {
  id: string;
  day: string;
  occasion: Occasion;
  explanation: string;
  worn: boolean;
  garments: Record<GarmentCategory, Garment | null>;
  // Slots the closet could only fill with something off the occasion.
  off_occasion: GarmentCategory[];
  forecast: { min_c: number; max_c: number; rain: boolean } | null;
};

export const OCCASIONS: { value: Occasion; label: string }[] = [
  { value: 'casual', label: 'Casual' },
  { value: 'work', label: 'Trabajo' },
  { value: 'night_out', label: 'Salir' },
  { value: 'formal', label: 'Formal' },
];

export function defaultOccasion(now = new Date()): Occasion {
  const day = now.getDay();
  const hour = now.getHours();
  const isWeekday = day >= 1 && day <= 5;
  if (isWeekday && hour < 17) return 'work';
  if ((day === 5 || day === 6) && hour >= 17) return 'night_out';
  return 'casual';
}

// Shared so an outfit requested from another screen lands on the occasion shown in Today.
export const useOccasion = create<{ occasion: Occasion; setOccasion: (next: Occasion) => void }>(
  (set) => ({ occasion: defaultOccasion(), setOccasion: (occasion) => set({ occasion }) })
);

function localDay(now = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const date = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${date}`;
}

// Minutes east of UTC; lets the server know when this phone's morning starts.
function utcOffsetMinutes(): number {
  return -new Date().getTimezoneOffset();
}

function coordsQuery(coords: Coords | null | undefined): string {
  return coords ? `&lat=${coords.lat}&lon=${coords.lon}` : '';
}

const HISTORY_KEY = ['outfit-history'];

export function useOutfitHistory() {
  return useQuery({ queryKey: HISTORY_KEY, queryFn: () => api<Outfit[]>('/outfits/history') });
}

function todayKey(occasion: Occasion) {
  return ['outfit', localDay(), occasion];
}

export function useTodayOutfit(occasion: Occasion, coords: Coords | null | undefined) {
  return useQuery({
    queryKey: todayKey(occasion),
    queryFn: () =>
      api<Outfit>(
        `/outfits/today?day=${localDay()}&occasion=${occasion}&tz=${utcOffsetMinutes()}${coordsQuery(coords)}`
      ),
    // Wait for the location so the first outfit of the day already matches the weather.
    enabled: coords !== undefined,
    retry: false,
  });
}

// Kept outside the component so its identity never changes between renders.
export function retryFailedOutfits(): void {
  void queryClient.refetchQueries({
    queryKey: ['outfit'],
    predicate: (query) => query.state.status === 'error',
  });
}

export function useAnotherOutfit(coords: Coords | null | undefined) {
  return useMutation({
    mutationFn: (outfit: Outfit) =>
      api<Outfit>(`/outfits/${outfit.id}/another?${coordsQuery(coords).slice(1)}`, {
        method: 'POST',
      }),
    onSuccess: (outfit) => queryClient.setQueryData(todayKey(outfit.occasion), outfit),
  });
}

export function useBuildAroundGarment(coords: Coords | null | undefined) {
  return useMutation({
    mutationFn: (garmentId: string) => {
      const { occasion } = useOccasion.getState();
      const query = `day=${localDay()}&occasion=${occasion}${coordsQuery(coords)}`;
      return api<Outfit>(`/outfits/around/${garmentId}?${query}`, { method: 'POST' });
    },
    onSuccess: (outfit) => queryClient.setQueryData(todayKey(outfit.occasion), outfit),
  });
}

export function useWearOutfit(coords: Coords | null | undefined) {
  return useMutation({
    mutationFn: (outfit: Outfit) =>
      api<Outfit>(`/outfits/${outfit.id}/wear?${coordsQuery(coords).slice(1)}`, { method: 'POST' }),
    onSuccess: (outfit) => {
      queryClient.setQueryData(todayKey(outfit.occasion), outfit);
      void refreshGarments();
      void queryClient.invalidateQueries({ queryKey: HISTORY_KEY });
    },
  });
}
