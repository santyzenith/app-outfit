import { router } from 'expo-router';
import { ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ChoiceChips } from '@/components/app/choice-chips';
import { Button } from '@/components/app/button';
import { Text } from '@/components/ui/text';
import { clearClosetFilters, colorFamily, useClosetFilters } from '@/lib/closet-filters';
import { FORMALITY_OPTIONS, useGarments, WARMTH_OPTIONS } from '@/lib/garments';

const ANY = 'any';

function Group({ label, children }: React.PropsWithChildren<{ label: string }>) {
  return (
    <View className="gap-2">
      <Text className="font-sans-medium text-sm text-muted-foreground">{label}</Text>
      {children}
    </View>
  );
}

export default function ClosetFiltersSheet() {
  const insets = useSafeAreaInsets();
  const filters = useClosetFilters();
  const { data: garments = [] } = useGarments();
  // Only colors that actually exist in this closet are offered.
  const colors = [...new Set(garments.map((g) => colorFamily(g.color)).filter(Boolean))]
    .sort()
    .map((color) => ({ value: color as string, label: color as string }));

  function set(patch: Partial<typeof filters>): void {
    useClosetFilters.setState(patch);
  }

  return (
    <ScrollView
      className="bg-background"
      contentContainerClassName="gap-5 p-5"
      contentContainerStyle={{ paddingBottom: insets.bottom + 20 }}>
      <Text className="font-serif-medium text-2xl">Filtros</Text>

      <Group label="Abrigo">
        <ChoiceChips
          layout="wrap"
          options={[{ value: ANY, label: 'Cualquiera' }, ...WARMTH_OPTIONS]}
          selected={filters.warmth ?? ANY}
          onSelect={(value) => set({ warmth: value === ANY ? null : value })}
        />
      </Group>

      <Group label="Formalidad">
        <ChoiceChips
          layout="wrap"
          options={[{ value: ANY, label: 'Cualquiera' }, ...FORMALITY_OPTIONS]}
          selected={filters.formality ?? ANY}
          onSelect={(value) => set({ formality: value === ANY ? null : value })}
        />
      </Group>

      {colors.length > 1 && (
        <Group label="Color">
          <ChoiceChips
            layout="wrap"
            options={[{ value: ANY, label: 'Cualquiera' }, ...colors]}
            selected={filters.color ?? ANY}
            onSelect={(value) => set({ color: value === ANY ? null : value })}
          />
        </Group>
      )}

      <View className="flex-row gap-3 pt-2">
        <Button variant="outline" size="lg" onPress={clearClosetFilters}>
          <Text className="font-sans-semibold">Quitar filtros</Text>
        </Button>
        <Button size="lg" className="flex-1" onPress={() => router.back()}>
          <Text className="font-sans-semibold">Ver prendas</Text>
        </Button>
      </View>
    </ScrollView>
  );
}
