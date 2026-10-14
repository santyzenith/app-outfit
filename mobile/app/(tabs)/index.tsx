import { Link } from 'expo-router';
import { CheckIcon, RefreshCwIcon } from 'lucide-react-native';
import * as React from 'react';
import { View } from 'react-native';

import { ChoiceChips } from '@/components/app/choice-chips';
import { OutfitCollage } from '@/components/app/outfit-collage';
import { OutfitTransition } from '@/components/app/outfit-transition';
import { Pulse } from '@/components/app/pulse';
import { ScreenHeader } from '@/components/app/screen-header';
import { Spinner } from '@/components/app/spinner';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { ApiError } from '@/lib/api';
import { type GarmentCategory, useGarments } from '@/lib/garments';
import { useCoords } from '@/lib/location';
import {
  OCCASIONS,
  type Outfit,
  retryFailedOutfits,
  useAnotherOutfit,
  useOccasion,
  useTodayOutfit,
  useWearOutfit,
} from '@/lib/outfits';

const MISSING_TEXT: Partial<Record<GarmentCategory, string>> = {
  top: 'una parte de arriba',
  bottom: 'una parte de abajo',
  shoes: 'un par de zapatos',
};

const SLOT_TEXT: Record<GarmentCategory, string> = {
  top: 'parte de arriba',
  bottom: 'parte de abajo',
  one_piece: 'pieza entera',
  outerwear: 'capa',
  shoes: 'zapatos',
  accessory: 'accesorio',
};

function offOccasionNote(outfit: Outfit): string | null {
  if (!outfit.off_occasion?.length) return null;
  const slots = outfit.off_occasion.map((category) => SLOT_TEXT[category]);
  const list =
    slots.length === 1 ? slots[0] : `${slots.slice(0, -1).join(', ')} ni ${slots.at(-1)}`;
  const occasion = OCCASIONS.find((option) => option.value === outfit.occasion)?.label;
  return `Aún no tienes ${list} para «${occasion}», así que usamos lo más cercano.`;
}

function todayLabel(): string {
  const label = new Date().toLocaleDateString('es', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function weatherLabel(forecast: Outfit['forecast']): string | null {
  if (!forecast) return null;
  const range = `${Math.round(forecast.min_c)}° a ${Math.round(forecast.max_c)}°`;
  return forecast.rain ? `${range} · probable lluvia` : range;
}

function Message({
  title,
  body,
  children,
}: React.PropsWithChildren<{ title: string; body: string }>) {
  return (
    <View className="flex-1 items-center justify-center gap-3 px-6">
      <Text className="text-center font-sans-semibold text-xl">{title}</Text>
      <Text className="text-center text-muted-foreground">{body}</Text>
      {children}
    </View>
  );
}

function NotEnoughGarments({ error }: { error: ApiError }) {
  const missing = (error.detail.missing as GarmentCategory[] | undefined) ?? [];
  const needs = missing.map((category) => MISSING_TEXT[category]).filter(Boolean);
  return (
    <Message
      title="Aún faltan prendas"
      body={`Para armar tu primer outfit necesitas ${needs.join(', ')}.`}>
      <Link href="/add" asChild>
        <Button size="lg">
          <Text className="font-sans-semibold">Añadir prendas</Text>
        </Button>
      </Link>
    </Message>
  );
}

export default function TodayScreen() {
  const coords = useCoords();
  const { occasion, setOccasion } = useOccasion();
  const today = useTodayOutfit(occasion, coords);
  const another = useAnotherOutfit(coords);
  const wear = useWearOutfit(coords);

  const outfit = today.data;

  // A failed attempt is only worth repeating once another garment has been catalogued.
  const { data: garments = [] } = useGarments();
  const readyCount = garments.filter((garment) => garment.status === 'ready').length;
  React.useEffect(retryFailedOutfits, [readyCount]);
  const noMoreOutfits =
    another.error instanceof ApiError && another.error.code === 'no_more_outfits';
  const busy = another.isPending || wear.isPending;

  function changeOccasion(next: typeof occasion): void {
    another.reset();
    setOccasion(next);
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader
        title="Tu outfit de hoy"
        eyebrow={[todayLabel(), weatherLabel(outfit?.forecast ?? null)].filter(Boolean).join(' · ')}
      />
      <View className="flex-1 gap-4 px-4 pb-4">
        <ChoiceChips options={OCCASIONS} selected={occasion} onSelect={changeOccasion} />

        {outfit ? (
          <>
            <OutfitTransition outfitId={outfit.id} dimmed={another.isPending}>
              <OutfitCollage outfit={outfit} />

              <Text className="text-center font-serif-italic text-lg leading-6">
                {outfit.explanation}
              </Text>
            </OutfitTransition>
            {offOccasionNote(outfit) && (
              <Text className="text-center text-sm text-muted-foreground">
                {offOccasionNote(outfit)}
              </Text>
            )}
            {noMoreOutfits && (
              <Text className="text-center text-sm text-muted-foreground">
                No hay más combinaciones por hoy con tu armario.
              </Text>
            )}

            {outfit.worn ? (
              <View className="h-12 flex-row items-center justify-center gap-2 rounded-md bg-secondary">
                <Icon as={CheckIcon} size={18} />
                <Text className="font-sans-medium">Hoy llevas este outfit</Text>
              </View>
            ) : (
              <View className="flex-row gap-3">
                <Button
                  variant="outline"
                  size="lg"
                  disabled={busy || noMoreOutfits}
                  onPress={() => another.mutate(outfit)}>
                  {another.isPending ? (
                    <Spinner size="small" />
                  ) : (
                    <Icon as={RefreshCwIcon} size={16} />
                  )}
                  <Text className="font-sans-semibold">Otra</Text>
                </Button>
                <Button
                  size="lg"
                  className="flex-1"
                  disabled={busy}
                  onPress={() => wear.mutate(outfit)}>
                  <Text className="font-sans-semibold">Me lo pongo</Text>
                </Button>
              </View>
            )}
          </>
        ) : today.error instanceof ApiError && today.error.code === 'not_enough_garments' ? (
          <NotEnoughGarments error={today.error} />
        ) : today.isError ? (
          <Message
            title="No pudimos armar tu outfit"
            body="Revisa tu conexión e inténtalo de nuevo.">
            <Button variant="outline" onPress={() => void today.refetch()}>
              <Text className="font-sans-semibold">Reintentar</Text>
            </Button>
          </Message>
        ) : (
          <Pulse style={{ flex: 1, gap: 16 }}>
            <View className="flex-1 rounded-3xl bg-muted" />
            <Text className="text-center font-serif-italic text-lg leading-6 text-muted-foreground">
              Armando tu outfit…
            </Text>
            <View className="h-12 rounded-md bg-muted" />
          </Pulse>
        )}
      </View>
    </View>
  );
}
