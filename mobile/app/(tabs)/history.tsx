import { Image } from 'expo-image';
import { FlatList, View } from 'react-native';

import { ScreenHeader } from '@/components/app/screen-header';
import { Spinner } from '@/components/app/spinner';
import { Text } from '@/components/ui/text';
import { type Garment, useGarmentImage } from '@/lib/garments';
import { OCCASIONS, type Outfit, useOutfitHistory } from '@/lib/outfits';

function dayLabel(day: string): string {
  // Parsed as a local date: `new Date('2026-10-13')` alone would mean midnight UTC.
  const [year, month, date] = day.split('-').map(Number);
  const label = new Date(year, month - 1, date).toLocaleDateString('es', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function Thumbnail({ garment }: { garment: Garment }) {
  const image = useGarmentImage(garment);
  return (
    <View className="aspect-square max-w-24 flex-1 overflow-hidden rounded-lg bg-white">
      <Image source={image} contentFit="contain" style={{ flex: 1 }} />
    </View>
  );
}

function HistoryEntry({ outfit }: { outfit: Outfit }) {
  const occasion = OCCASIONS.find((option) => option.value === outfit.occasion)?.label;
  const garments = Object.values(outfit.garments).filter((garment) => garment !== null);

  return (
    <View className="gap-3 rounded-2xl border border-border bg-card p-4">
      <View className="flex-row items-baseline justify-between">
        <Text className="font-sans-semibold">{dayLabel(outfit.day)}</Text>
        <Text className="text-sm text-muted-foreground">{occasion}</Text>
      </View>
      <View className="flex-row gap-2">
        {garments.map((garment) => (
          <Thumbnail key={garment.id} garment={garment} />
        ))}
      </View>
    </View>
  );
}

export default function HistoryScreen() {
  const { data: outfits = [], isLoading, isError, refetch, isRefetching } = useOutfitHistory();

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Historial" eyebrow="Lo que te has puesto" />

      {isLoading ? (
        <View className="flex-1 items-center justify-center">
          <Spinner />
        </View>
      ) : (
        <FlatList
          data={outfits}
          keyExtractor={(outfit) => outfit.id}
          renderItem={({ item }) => <HistoryEntry outfit={item} />}
          contentContainerClassName="grow gap-3 px-4 pb-4 pt-1"
          onRefresh={() => void refetch()}
          refreshing={isRefetching}
          ListEmptyComponent={
            <View className="flex-1 items-center justify-center gap-2 px-8">
              <Text className="text-center font-sans-semibold text-lg">
                {isError ? 'No pudimos cargar tu historial' : 'Aún no hay nada aquí'}
              </Text>
              <Text className="text-center text-muted-foreground">
                {isError
                  ? 'Desliza hacia abajo para intentarlo de nuevo.'
                  : 'Cuando toques "Me lo pongo" en un outfit, aparecerá en esta lista.'}
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}
