import { Image } from 'expo-image';
import { router } from 'expo-router';
import { ChevronLeftIcon, ChevronRightIcon, Trash2Icon } from 'lucide-react-native';
import * as React from 'react';
import { Alert, Pressable, ScrollView, View } from 'react-native';

import { OutfitCollage } from '@/components/app/outfit-collage';
import { ScreenHeader } from '@/components/app/screen-header';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { type Garment, useGarmentImage } from '@/lib/garments';
import { localDay, OCCASIONS, type Outfit, useCalendar, useDeleteOutfit } from '@/lib/outfits';
import { cn } from '@/lib/utils';

const WEEKDAYS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// Weeks start on Monday; the grid always shows whole weeks.
function monthGrid(month: Date): Date[][] {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const start = new Date(first);
  start.setDate(1 - ((first.getDay() + 6) % 7));
  const weeks: Date[][] = [];
  const cursor = new Date(start);
  do {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(week);
  } while (cursor.getMonth() === month.getMonth());
  return weeks;
}

function mainGarment(outfit: Outfit): Garment | null {
  const { one_piece, top, bottom, shoes } = outfit.garments;
  return one_piece ?? top ?? bottom ?? shoes;
}

function CellThumb({ garment }: { garment: Garment }) {
  const image = useGarmentImage(garment);
  return (
    <View className="h-7 w-7 overflow-hidden rounded-md bg-white">
      <Image source={image} contentFit="contain" style={{ flex: 1 }} />
    </View>
  );
}

function DayCell({
  date,
  inMonth,
  selected,
  isToday,
  outfit,
  onPress,
}: {
  date: Date;
  inMonth: boolean;
  selected: boolean;
  isToday: boolean;
  outfit: Outfit | undefined;
  onPress: () => void;
}) {
  const garment = outfit ? mainGarment(outfit) : null;
  return (
    <Pressable
      onPress={onPress}
      className={cn(
        'h-16 flex-1 items-center gap-1 rounded-xl pt-1.5',
        selected && 'bg-secondary',
        !inMonth && 'opacity-30'
      )}>
      <Text
        className={cn(
          'text-sm',
          isToday && 'font-sans-bold',
          isToday && !selected && 'text-primary underline'
        )}>
        {date.getDate()}
      </Text>
      {garment && outfit?.worn ? (
        <CellThumb garment={garment} />
      ) : outfit?.planned ? (
        <View className="h-2 w-2 rounded-full border border-foreground" />
      ) : null}
    </Pressable>
  );
}

function DayOutfit({ outfit }: { outfit: Outfit }) {
  const remove = useDeleteOutfit();
  const occasion = OCCASIONS.find((option) => option.value === outfit.occasion)?.label;

  function confirmDelete(): void {
    Alert.alert(
      outfit.worn ? '¿Quitar este registro?' : '¿Quitar este plan?',
      'Tus prendas no se tocan.',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Quitar', style: 'destructive', onPress: () => remove.mutate(outfit.id) },
      ]
    );
  }

  return (
    <View className="gap-2">
      <View className="flex-row items-center justify-between">
        <Text className="font-sans-medium">
          {outfit.worn ? 'Te lo pusiste' : 'Planeado'} · {occasion}
        </Text>
        <Pressable accessibilityLabel="Quitar" hitSlop={10} onPress={confirmDelete}>
          <Icon as={Trash2Icon} size={18} className="text-muted-foreground" />
        </Pressable>
      </View>
      <View className="h-64">
        <OutfitCollage garments={outfit.garments} />
      </View>
    </View>
  );
}

export default function CalendarScreen() {
  const today = localDay();
  const [month, setMonth] = React.useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [selectedDay, setSelectedDay] = React.useState(today);

  const weeks = monthGrid(month);
  const start = localDay(weeks[0][0]);
  const end = localDay(weeks[weeks.length - 1][6]);
  const { data: outfits = [] } = useCalendar(start, end);

  const byDay = new Map<string, Outfit[]>();
  for (const outfit of outfits) byDay.set(outfit.day, [...(byDay.get(outfit.day) ?? []), outfit]);
  const dayOutfits = byDay.get(selectedDay) ?? [];

  const [year, monthIndex, date] = selectedDay.split('-').map(Number);
  const selectedLabel = capitalize(
    new Date(year, monthIndex - 1, date).toLocaleDateString('es', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    })
  );

  function shiftMonth(delta: number): void {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  }

  function openBuilder(mode: 'wear' | 'plan'): void {
    router.push({ pathname: '/outfit/new', params: { day: selectedDay, mode } });
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Calendario" eyebrow="Lo que te pusiste y lo que planeas" />
      <ScrollView contentContainerClassName="gap-4 px-4 pb-10">
        <View className="flex-row items-center justify-between">
          <Pressable accessibilityLabel="Mes anterior" hitSlop={12} onPress={() => shiftMonth(-1)}>
            <Icon as={ChevronLeftIcon} size={22} />
          </Pressable>
          <Text className="font-sans-semibold text-lg">
            {capitalize(month.toLocaleDateString('es', { month: 'long', year: 'numeric' }))}
          </Text>
          <Pressable accessibilityLabel="Mes siguiente" hitSlop={12} onPress={() => shiftMonth(1)}>
            <Icon as={ChevronRightIcon} size={22} />
          </Pressable>
        </View>

        <View className="gap-1">
          <View className="flex-row">
            {WEEKDAYS.map((weekday, index) => (
              <Text key={index} className="flex-1 text-center text-xs text-muted-foreground">
                {weekday}
              </Text>
            ))}
          </View>
          {weeks.map((week) => (
            <View key={localDay(week[0])} className="flex-row">
              {week.map((cellDate) => {
                const key = localDay(cellDate);
                const cellOutfits = byDay.get(key);
                return (
                  <DayCell
                    key={key}
                    date={cellDate}
                    inMonth={cellDate.getMonth() === month.getMonth()}
                    selected={key === selectedDay}
                    isToday={key === today}
                    outfit={cellOutfits?.find((item) => item.worn) ?? cellOutfits?.[0]}
                    onPress={() => setSelectedDay(key)}
                  />
                );
              })}
            </View>
          ))}
        </View>

        <View className="gap-4 rounded-3xl border border-border p-4">
          <Text className="font-serif-medium text-2xl">{selectedLabel}</Text>
          {dayOutfits.length === 0 && (
            <Text className="text-muted-foreground">
              {selectedDay > today ? 'Aún no hay nada planeado.' : 'No registraste nada este día.'}
            </Text>
          )}
          {dayOutfits.map((outfit) => (
            <DayOutfit key={outfit.id} outfit={outfit} />
          ))}
          <View className="gap-2">
            {selectedDay <= today && (
              <Button variant="outline" onPress={() => openBuilder('wear')}>
                <Text className="font-sans-semibold">Registrar lo que me puse</Text>
              </Button>
            )}
            {selectedDay >= today && (
              <Button variant="outline" onPress={() => openBuilder('plan')}>
                <Text className="font-sans-semibold">Planear un outfit</Text>
              </Button>
            )}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}
