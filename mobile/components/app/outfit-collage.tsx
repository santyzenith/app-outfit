import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Pressable, View } from 'react-native';

import { type Garment, useGarmentImage } from '@/lib/garments';
import type { Outfit } from '@/lib/outfits';

type Slot = { garment: Garment; weight: number };

function Piece({ garment, weight }: Slot) {
  const image = useGarmentImage(garment);
  return (
    <Pressable
      accessibilityLabel={garment.name ?? undefined}
      style={{ flex: weight }}
      onPress={() => router.push({ pathname: '/garment/[id]', params: { id: garment.id } })}>
      <Image source={image} contentFit="contain" style={{ flex: 1 }} transition={150} />
    </Pressable>
  );
}

function Column({ slots }: { slots: Slot[] }) {
  return (
    <View className="flex-1 gap-1">
      {slots.map((slot) => (
        <Piece key={slot.garment.id} {...slot} />
      ))}
    </View>
  );
}

function slots(...entries: [Garment | null, number][]): Slot[] {
  return entries.flatMap(([garment, weight]) => (garment ? [{ garment, weight }] : []));
}

// Two columns like a flat lay: what goes on top at the left, the long piece and shoes at the right.
// The canvas stays white in dark mode too: garment images come on a white background.
export function OutfitCollage({ garments }: { garments: Outfit['garments'] }) {
  const { top, bottom, one_piece, outerwear, shoes, accessory } = garments;

  const columns = one_piece
    ? [slots([one_piece, 1]), slots([outerwear, 3], [shoes, 2], [accessory, 2])]
    : [slots([outerwear, 3], [top, 3], [accessory, 2]), slots([bottom, 3], [shoes, 2])];

  return (
    <View className="flex-1 flex-row gap-1 rounded-3xl bg-white p-3">
      {columns
        .filter((column) => column.length > 0)
        .map((column) => (
          <Column key={column[0].garment.id} slots={column} />
        ))}
    </View>
  );
}
