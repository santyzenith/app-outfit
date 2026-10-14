import { useMutation, useQuery } from '@tanstack/react-query';

import { api, jsonBody } from '@/lib/api';
import { API_URL } from '@/lib/config';
import {
  type Garment,
  type GarmentCategory,
  type ImageSize,
  refreshGarments,
} from '@/lib/garments';
import { queryClient } from '@/lib/query';
import { useSession } from '@/lib/session';

export type BasicColor = {
  key: string;
  // Agrees with the shape: "blanca" for "Camiseta", "blanco" for "Jean".
  name: string;
  swatch: string;
  // Already in the closet in this color.
  owned: boolean;
};

export type Basic = {
  key: string;
  name: string;
  category: GarmentCategory;
  colors: BasicColor[];
};

const BASICS_KEY = ['basics'];

export function useBasics() {
  return useQuery({ queryKey: BASICS_KEY, queryFn: () => api<Basic[]>('/basics') });
}

export function useAddBasics() {
  return useMutation({
    mutationFn: (keys: string[]) => api<Garment[]>('/basics', jsonBody('POST', { keys })),
    onSettled: () =>
      Promise.all([refreshGarments(), queryClient.invalidateQueries({ queryKey: BASICS_KEY })]),
  });
}

export function useBasicImage(shape: string, color: string, size: ImageSize = 'thumb') {
  const accessToken = useSession((state) => state.accessToken);
  return {
    uri: `${API_URL}/v1/basics/${shape}/image?color=${color}&size=${size}`,
    headers: { Authorization: `Bearer ${accessToken}` },
  };
}
