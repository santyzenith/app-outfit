import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import * as React from 'react';
import { Alert, ScrollView, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { ChoiceChips } from '@/components/app/choice-chips';
import { GarmentSkeleton } from '@/components/app/skeletons';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Text } from '@/components/ui/text';
import {
  CATEGORY_OPTIONS,
  FORMALITY_OPTIONS,
  type Garment,
  type GarmentEdit,
  useDeleteGarment,
  useGarmentImage,
  useGarments,
  useUpdateGarment,
  WARMTH_OPTIONS,
} from '@/lib/garments';
import { useCoords } from '@/lib/location';
import { useBuildAroundGarment } from '@/lib/outfits';

function Field({ label, children }: React.PropsWithChildren<{ label: string }>) {
  return (
    <View className="gap-2">
      <Text className="font-sans-medium text-sm text-muted-foreground">{label}</Text>
      {children}
    </View>
  );
}

function wearSummary(garment: Garment): string {
  if (!garment.last_worn_at) return 'Aún no te la has puesto';
  const times = garment.wear_count === 1 ? '1 vez' : `${garment.wear_count} veces`;
  const last = new Date(garment.last_worn_at).toLocaleDateString('es', {
    day: 'numeric',
    month: 'long',
  });
  return `Usada ${times} · la última, el ${last}`;
}

// Mounted only once the garment is loaded, so the form can start from its values.
function GarmentForm({ garment }: { garment: Garment }) {
  const [showOriginal, setShowOriginal] = React.useState(false);
  const image = useGarmentImage(garment, { variant: showOriginal ? 'original' : undefined });
  const update = useUpdateGarment();
  const remove = useDeleteGarment();
  const buildAround = useBuildAroundGarment(useCoords());
  const [form, setForm] = React.useState<GarmentEdit>({
    name: garment.name ?? '',
    category: garment.category,
    warmth: garment.warmth,
    formality: garment.formality,
    brand: garment.brand ?? '',
    size: garment.size ?? '',
    notes: garment.notes ?? '',
  });
  const hasDetails = Boolean(garment.brand || garment.size || garment.notes);
  const [showDetails, setShowDetails] = React.useState(hasDetails);

  const changed =
    form.name !== (garment.name ?? '') ||
    form.category !== garment.category ||
    form.warmth !== garment.warmth ||
    form.formality !== garment.formality ||
    form.brand !== (garment.brand ?? '') ||
    form.size !== (garment.size ?? '') ||
    form.notes !== (garment.notes ?? '');
  const canSave = changed && form.name.trim().length > 0 && !update.isPending;

  function save(): void {
    update.mutate({ id: garment.id, changes: { ...form, name: form.name.trim() } });
  }

  function confirmDelete(): void {
    Alert.alert('¿Eliminar esta prenda?', 'Se borrará de tu armario.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar',
        style: 'destructive',
        onPress: () => remove.mutate(garment.id, { onSuccess: () => router.back() }),
      },
    ]);
  }

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerClassName="gap-5 p-4 pb-10"
      keyboardShouldPersistTaps="handled">
      <View className="aspect-square overflow-hidden rounded-2xl bg-white">
        <Image source={image} contentFit="contain" style={{ flex: 1 }} transition={150} />
      </View>
      <Text className="text-center text-sm text-muted-foreground">{wearSummary(garment)}</Text>
      <Button variant="ghost" size="sm" onPress={() => setShowOriginal((value) => !value)}>
        <Text className="font-sans-semibold">
          {showOriginal ? 'Ver imagen del armario' : 'Ver mi foto original'}
        </Text>
      </Button>

      <Field label="Nombre">
        <Input
          value={form.name}
          onChangeText={(name) => setForm((current) => ({ ...current, name }))}
          maxLength={120}
          returnKeyType="done"
        />
      </Field>

      <Field label="Tipo">
        <ChoiceChips
          layout="wrap"
          options={CATEGORY_OPTIONS}
          selected={form.category}
          onSelect={(category) => setForm((current) => ({ ...current, category }))}
        />
      </Field>

      <Field label="Abrigo">
        <ChoiceChips
          options={WARMTH_OPTIONS}
          selected={form.warmth}
          onSelect={(warmth) => setForm((current) => ({ ...current, warmth }))}
        />
      </Field>

      <Field label="Formalidad">
        <ChoiceChips
          options={FORMALITY_OPTIONS}
          selected={form.formality}
          onSelect={(formality) => setForm((current) => ({ ...current, formality }))}
        />
      </Field>

      {showDetails ? (
        <Animated.View entering={FadeInDown.duration(250)} className="gap-5">
          <View className="flex-row gap-3">
            <View className="flex-1">
              <Field label="Marca">
                <Input
                  value={form.brand}
                  onChangeText={(brand) => setForm((current) => ({ ...current, brand }))}
                  maxLength={60}
                  className="font-sans"
                />
              </Field>
            </View>
            <View className="w-28">
              <Field label="Talla">
                <Input
                  value={form.size}
                  onChangeText={(size) => setForm((current) => ({ ...current, size }))}
                  maxLength={20}
                  autoCapitalize="characters"
                  className="font-sans"
                />
              </Field>
            </View>
          </View>
          <Field label="Notas">
            <Input
              value={form.notes}
              onChangeText={(notes) => setForm((current) => ({ ...current, notes }))}
              maxLength={500}
              multiline
              placeholder="Por ejemplo: lavar a mano"
              className="h-20 py-2 font-sans"
              style={{ textAlignVertical: 'top' }}
            />
          </Field>
        </Animated.View>
      ) : (
        <Button variant="ghost" size="sm" onPress={() => setShowDetails(true)}>
          <Text className="font-sans-semibold">Añadir marca, talla o notas</Text>
        </Button>
      )}

      {update.isError && (
        <Text className="text-center text-sm text-destructive">
          No pudimos guardar los cambios. Inténtalo de nuevo.
        </Text>
      )}

      <Button size="lg" disabled={!canSave} onPress={save}>
        <Text className="font-sans-semibold">
          {update.isPending ? 'Guardando…' : 'Guardar cambios'}
        </Text>
      </Button>
      <Button
        variant="outline"
        size="lg"
        disabled={buildAround.isPending}
        onPress={() => buildAround.mutate(garment.id, { onSuccess: () => router.dismissTo('/') })}>
        <Text className="font-sans-semibold">
          {buildAround.isPending ? 'Armando…' : 'Armar un outfit con esta prenda'}
        </Text>
      </Button>
      {buildAround.isError && (
        <Text className="text-center text-sm text-muted-foreground">
          Aún no hay prendas suficientes para combinarla.
        </Text>
      )}
      <Button variant="ghost" onPress={confirmDelete}>
        <Text className="text-destructive">Eliminar prenda</Text>
      </Button>
    </ScrollView>
  );
}

export default function GarmentScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: garments, isLoading } = useGarments();
  const garment = garments?.find((item) => item.id === id);

  if (garment) return <GarmentForm garment={garment} />;

  if (isLoading) {
    return (
      <View className="flex-1 bg-background">
        <GarmentSkeleton />
      </View>
    );
  }

  return (
    <View className="flex-1 items-center justify-center bg-background px-8">
      <Text className="text-center">Esta prenda ya no existe.</Text>
    </View>
  );
}
