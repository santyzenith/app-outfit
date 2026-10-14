import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Pressable, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { type Garment, useGarmentImage } from '@/lib/garments';
import type { Outfit } from '@/lib/outfits';

// Pieces arrive one after another, like clothes laid on a bed.
const STAGGER_MS = 70;

type Slot = { garment: Garment; weight: number; order: number };

function Piece({ garment, weight, order }: Slot) {
  const image = useGarmentImage(garment);
  return (
    <Animated.View
      entering={FadeInDown.duration(380).delay(order * STAGGER_MS)}
      style={{ flex: weight }}>
      <Pressable
        accessibilityLabel={garment.name ?? undefined}
        style={{ flex: 1 }}
        onPress={() => router.push({ pathname: '/garment/[id]', params: { id: garment.id } })}>
        <Image source={image} contentFit="contain" style={{ flex: 1 }} transition={150} />
      </Pressable>
    </Animated.View>
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

// Reading order of the collage: outer layer first, shoes and accessory last.
const ORDER = ['outerwear', 'top', 'one_piece', 'bottom', 'shoes', 'accessory'];

function slots(...entries: [Garment | null, number][]): Slot[] {
  return entries.flatMap(([garment, weight]) =>
    garment ? [{ garment, weight, order: ORDER.indexOf(garment.category ?? '') }] : []
  );
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
