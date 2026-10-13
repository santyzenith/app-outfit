import { Link } from 'expo-router';
import { PlusIcon } from 'lucide-react-native';
import { FlatList, View } from 'react-native';

import { GarmentTile } from '@/components/app/garment-tile';
import { ScreenHeader } from '@/components/app/screen-header';
import { Spinner } from '@/components/app/spinner';
import { UploadBanner } from '@/components/app/upload-banner';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useGarments } from '@/lib/garments';

const COLUMNS = 3;

function closetSummary(count: number): string {
  if (count === 0) return 'Aquí vivirá tu ropa';
  return count === 1 ? '1 prenda' : `${count} prendas`;
}

export default function ClosetScreen() {
  const { data: garments = [], isLoading, isError, refetch, isRefetching } = useGarments();

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Armario" eyebrow={closetSummary(garments.length)} />
      <UploadBanner />

      {isLoading ? (
        <View className="flex-1 items-center justify-center">
          <Spinner />
        </View>
      ) : (
        <FlatList
          data={garments}
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
                {isError ? 'No pudimos cargar tu armario' : 'Tu armario está vacío'}
              </Text>
              <Text className="text-center text-muted-foreground">
                {isError
                  ? 'Desliza hacia abajo para intentarlo de nuevo.'
                  : 'Añade tus primeras prendas con el botón de abajo.'}
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
