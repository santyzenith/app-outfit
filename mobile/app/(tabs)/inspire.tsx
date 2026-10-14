import * as ImagePicker from 'expo-image-picker';
import { ImagePlusIcon } from 'lucide-react-native';
import { FlatList, View } from 'react-native';

import { LookCard } from '@/components/app/look-card';
import { Pulse } from '@/components/app/pulse';
import { ScreenHeader } from '@/components/app/screen-header';
import { Button } from '@/components/app/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useInspirations, useUploadLook } from '@/lib/inspirations';

export default function InspireScreen() {
  const { data: looks = [], isLoading, isError, refetch, isRefetching } = useInspirations();
  const upload = useUploadLook();

  async function pickLook(): Promise<void> {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1,
    });
    if (!result.canceled) upload.mutate(result.assets[0].uri);
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Inspira" eyebrow="Un look que te gusta, armado con tu ropa" />
      {upload.isError && (
        <Text className="px-4 pb-2 text-sm text-destructive">
          No pudimos subir la foto. Inténtalo de nuevo.
        </Text>
      )}

      {isLoading ? (
        <Pulse style={{ gap: 12, paddingHorizontal: 16, paddingTop: 4 }}>
          {[0, 1].map((entry) => (
            <View key={entry} className="h-40 rounded-2xl bg-muted" />
          ))}
        </Pulse>
      ) : (
        <FlatList
          data={looks}
          keyExtractor={(look) => look.id}
          renderItem={({ item }) => <LookCard inspiration={item} />}
          contentContainerClassName="grow gap-3 px-4 pb-28 pt-1"
          onRefresh={() => void refetch()}
          refreshing={isRefetching}
          ListEmptyComponent={
            <View className="flex-1 items-center justify-center gap-2 px-8">
              <Text className="text-center font-sans-semibold text-lg">
                {isError ? 'No pudimos cargar tus looks' : '¿Viste un look que te encantó?'}
              </Text>
              <Text className="text-center text-muted-foreground">
                {isError
                  ? 'Desliza hacia abajo para intentarlo de nuevo.'
                  : 'Guarda una captura de la foto o publicación y súbela. Lo armamos con lo que ya tienes y te decimos qué te falta.'}
              </Text>
            </View>
          }
        />
      )}

      <Button
        size="lg"
        disabled={upload.isPending}
        className="absolute bottom-6 right-4 rounded-full shadow-md"
        onPress={() => void pickLook()}>
        <Icon as={ImagePlusIcon} size={20} className="text-primary-foreground" />
        <Text className="font-sans-semibold">{upload.isPending ? 'Subiendo…' : 'Nuevo look'}</Text>
      </Button>
    </View>
  );
}
