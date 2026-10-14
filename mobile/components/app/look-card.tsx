import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Trash2Icon } from 'lucide-react-native';
import { Pressable, View } from 'react-native';

import { Spinner } from '@/components/app/spinner';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { type Garment, useGarmentImage } from '@/lib/garments';
import { type Inspiration, useDeleteInspiration, useInspirationImage } from '@/lib/inspirations';

function Thumb({ garment }: { garment: Garment }) {
  const image = useGarmentImage(garment, { size: 'thumb' });
  return (
    <View className="h-14 w-14 overflow-hidden rounded-lg bg-white">
      <Image source={image} contentFit="contain" style={{ flex: 1 }} />
    </View>
  );
}

function Matched({ inspiration }: { inspiration: Inspiration }) {
  const garments = Object.values(inspiration.garments).filter((garment) => garment !== null);
  const missing = inspiration.missing.map((piece) => piece.name.toLowerCase()).join(', ');
  return (
    <View className="flex-1 gap-2">
      <Text className="font-sans-semibold">
        {garments.length === 0 ? 'Nada parecido en tu armario' : 'Con tu ropa'}
      </Text>
      <View className="flex-row flex-wrap gap-1.5">
        {garments.map((garment) => (
          <Thumb key={garment.id} garment={garment} />
        ))}
      </View>
      {missing ? (
        <Text numberOfLines={2} className="text-sm text-muted-foreground">
          Te falta: {missing}
        </Text>
      ) : null}
    </View>
  );
}

export function LookCard({ inspiration }: { inspiration: Inspiration }) {
  const photo = useInspirationImage(inspiration, 'thumb');
  const remove = useDeleteInspiration();
  const ready = inspiration.status === 'ready';

  return (
    <Pressable
      disabled={!ready}
      onPress={() => router.push({ pathname: '/look/[id]', params: { id: inspiration.id } })}
      className="flex-row gap-3 rounded-2xl border border-border bg-card p-3 active:opacity-80">
      <View className="aspect-[3/4] w-24 overflow-hidden rounded-xl bg-muted">
        <Image source={photo} contentFit="cover" style={{ flex: 1 }} transition={150} />
      </View>

      {ready ? (
        <Matched inspiration={inspiration} />
      ) : inspiration.status === 'processing' ? (
        <View className="flex-1 flex-row items-center gap-3">
          <Spinner size="small" />
          <Text className="text-muted-foreground">Buscando en tu armario…</Text>
        </View>
      ) : (
        <View className="flex-1 justify-center gap-3">
          <Text className="text-muted-foreground">
            {inspiration.failure_reason === 'not_a_look'
              ? 'No encontramos un look en esta foto.'
              : 'No pudimos analizar esta foto.'}
          </Text>
          <Pressable
            accessibilityLabel="Eliminar"
            hitSlop={8}
            className="flex-row items-center gap-2"
            onPress={() => remove.mutate(inspiration.id)}>
            <Icon as={Trash2Icon} size={18} className="text-destructive" />
            <Text className="text-destructive">Eliminar</Text>
          </Pressable>
        </View>
      )}
    </Pressable>
  );
}
