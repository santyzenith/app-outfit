import { Image } from 'expo-image';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import * as React from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ChoiceChips } from '@/components/app/choice-chips';
import { OutfitCollage } from '@/components/app/outfit-collage';
import { Button } from '@/components/ui/button';
import { Text } from '@/components/ui/text';
import { type Garment, type GarmentCategory, useGarmentImage, useGarments } from '@/lib/garments';
import { OCCASIONS, type Outfit, useCreateOutfit, useOccasion } from '@/lib/outfits';
import { cn } from '@/lib/utils';

const SLOTS: { category: GarmentCategory; label: string }[] = [
  { category: 'top', label: 'Arriba' },
  { category: 'bottom', label: 'Abajo' },
  { category: 'one_piece', label: 'Pieza entera' },
  { category: 'outerwear', label: 'Capa' },
  { category: 'shoes', label: 'Zapatos' },
  { category: 'accessory', label: 'Accesorio' },
];

const TILE = 80;

type Selection = Outfit['garments'];

const EMPTY: Selection = {
  top: null,
  bottom: null,
  one_piece: null,
  outerwear: null,
  shoes: null,
  accessory: null,
};

function select(current: Selection, garment: Garment): Selection {
  const category = garment.category as GarmentCategory;
  const next = { ...current, [category]: current[category]?.id === garment.id ? null : garment };
  // A dress or jumpsuit replaces separates, and the other way round.
  if (category === 'one_piece' && next.one_piece) next.top = next.bottom = null;
  if ((category === 'top' || category === 'bottom') && next[category]) next.one_piece = null;
  return next;
}

function missingHint(selection: Selection): string | null {
  const hasBase = selection.one_piece || (selection.top && selection.bottom);
  if (!hasBase && !selection.shoes) return 'Elige una base y unos zapatos.';
  if (!hasBase) return 'Falta la base: arriba y abajo, o una pieza entera.';
  if (!selection.shoes) return 'Faltan los zapatos.';
  return null;
}

function Tile({
  garment,
  selected,
  onPress,
}: {
  garment: Garment;
  selected: boolean;
  onPress: () => void;
}) {
  const image = useGarmentImage(garment);
  return (
    <Pressable
      accessibilityLabel={garment.name ?? undefined}
      accessibilityState={{ selected }}
      onPress={onPress}
      style={{ width: TILE, height: TILE }}
      className={cn(
        'overflow-hidden rounded-xl border-2 bg-white',
        selected ? 'border-primary' : 'border-border'
      )}>
      <Image source={image} contentFit="contain" style={{ flex: 1 }} />
    </Pressable>
  );
}

export default function NewOutfitScreen() {
  const { day, mode } = useLocalSearchParams<{ day: string; mode: 'wear' | 'plan' }>();
  const { data: garments = [] } = useGarments();
  const [selection, setSelection] = React.useState<Selection>(EMPTY);
  const [occasion, setOccasion] = React.useState(useOccasion.getState().occasion);
  const create = useCreateOutfit();
  const insets = useSafeAreaInsets();

  const ready = garments.filter((garment) => garment.status === 'ready');
  const hint = missingHint(selection);

  function save(): void {
    const ids = Object.fromEntries(
      Object.entries(selection).map(([category, garment]) => [category, garment?.id ?? null])
    );
    create.mutate(
      { day, occasion, worn: mode === 'wear', garments: ids },
      { onSuccess: () => router.back() }
    );
  }

  return (
    <View className="flex-1 bg-background">
      <Stack.Screen options={{ title: mode === 'wear' ? 'Lo que me puse' : 'Planear outfit' }} />
      <View className="h-56 px-4 pt-4">
        {Object.values(selection).some(Boolean) ? (
          <OutfitCollage garments={selection} />
        ) : (
          <View className="flex-1 items-center justify-center rounded-3xl bg-muted px-8">
            <Text className="text-center text-muted-foreground">
              Toca tus prendas abajo para armar el outfit.
            </Text>
          </View>
        )}
      </View>
      <ScrollView contentContainerClassName="gap-5 p-4 pb-40">
        <ChoiceChips options={OCCASIONS} selected={occasion} onSelect={setOccasion} />

        {SLOTS.map(({ category, label }) => {
          const options = ready.filter((garment) => garment.category === category);
          if (options.length === 0) return null;
          return (
            <View key={category} className="gap-2">
              <Text className="font-sans-medium text-sm text-muted-foreground">{label}</Text>
              {/* A horizontal ScrollView grows to fill the screen unless told not to. */}
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={{ flexGrow: 0, height: TILE }}
                contentContainerClassName="gap-2">
                {options.map((garment) => (
                  <Tile
                    key={garment.id}
                    garment={garment}
                    selected={selection[category]?.id === garment.id}
                    onPress={() => setSelection((current) => select(current, garment))}
                  />
                ))}
              </ScrollView>
            </View>
          );
        })}
      </ScrollView>

      <View
        className="absolute inset-x-0 bottom-0 gap-2 border-t border-border bg-background px-4 pt-3"
        style={{ paddingBottom: insets.bottom + 12 }}>
        {create.isError ? (
          <Text className="text-center text-sm text-destructive">
            No pudimos guardarlo. Inténtalo de nuevo.
          </Text>
        ) : hint ? (
          <Text className="text-center text-sm text-muted-foreground">{hint}</Text>
        ) : null}
        <Button size="lg" disabled={hint !== null || create.isPending} onPress={save}>
          <Text className="font-sans-semibold">
            {create.isPending
              ? 'Guardando…'
              : mode === 'wear'
                ? 'Guardar en el calendario'
                : 'Planear'}
          </Text>
        </Button>
      </View>
    </View>
  );
}
