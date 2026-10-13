import { Link } from 'expo-router';
import { PlusIcon } from 'lucide-react-native';
import * as React from 'react';
import { FlatList, ScrollView, View } from 'react-native';

import { ChoiceChips } from '@/components/app/choice-chips';
import { GarmentTile } from '@/components/app/garment-tile';
import { ScreenHeader } from '@/components/app/screen-header';
import { Spinner } from '@/components/app/spinner';
import { UploadBanner } from '@/components/app/upload-banner';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { type GarmentCategory, useGarments } from '@/lib/garments';

const COLUMNS = 3;

type Filter = GarmentCategory | 'all';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'Todo' },
  { value: 'top', label: 'Arriba' },
  { value: 'bottom', label: 'Abajo' },
  { value: 'one_piece', label: 'Enteras' },
  { value: 'outerwear', label: 'Capas' },
  { value: 'shoes', label: 'Zapatos' },
  { value: 'accessory', label: 'Accesorios' },
];

function closetSummary(count: number): string {
  if (count === 0) return 'Aquí vivirá tu ropa';
  return count === 1 ? '1 prenda' : `${count} prendas`;
}

export default function ClosetScreen() {
  const { data: garments = [], isLoading, isError, refetch, isRefetching } = useGarments();
  const [filter, setFilter] = React.useState<Filter>('all');

  // Garments still being catalogued have no category yet, so they only show under "Todo".
  const visible = filter === 'all' ? garments : garments.filter((g) => g.category === filter);

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Armario" eyebrow={closetSummary(garments.length)} />
      <UploadBanner />

      {garments.length > 0 && (
        // A horizontal ScrollView grows to fill the screen unless told not to.
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={{ flexGrow: 0 }}
          contentContainerClassName="px-4 pb-3">
          <ChoiceChips layout="wrap" options={FILTERS} selected={filter} onSelect={setFilter} />
        </ScrollView>
      )}

      {isLoading ? (
        <View className="flex-1 items-center justify-center">
          <Spinner />
        </View>
      ) : (
        <FlatList
          data={visible}
          keyExtractor={(garment) => garment.id}
          numColumns={COLUMNS}
          renderItem={({ item }) => <GarmentTile garment={item} />}
          columnWrapperClassName="gap-2"
          contentContainerClassName="grow gap-2 px-4 pb-28 pt-1"
          onRefresh={() => void refetch()}
          refreshing={isRefetching}
          ListEmptyComponent={
            <View className="flex-1 items-center justify-center gap-2 px-8">
              <Text className="text-center font-sans-semibold text-lg">
                {isError
                  ? 'No pudimos cargar tu armario'
                  : garments.length > 0
                    ? 'Nada de este tipo todavía'
                    : 'Tu armario está vacío'}
              </Text>
              <Text className="text-center text-muted-foreground">
                {isError
                  ? 'Desliza hacia abajo para intentarlo de nuevo.'
                  : 'Añade prendas con el botón de abajo.'}
              </Text>
            </View>
          }
        />
      )}

      <Link href="/add" asChild>
        <Button size="lg" className="absolute bottom-6 right-4 rounded-full shadow-md">
          <Icon as={PlusIcon} size={20} className="text-primary-foreground" />
          <Text className="font-sans-semibold">Añadir prendas</Text>
        </Button>
      </Link>
    </View>
  );
}
