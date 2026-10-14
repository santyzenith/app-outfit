import { Image } from 'expo-image';
import { router } from 'expo-router';
import { CheckIcon } from 'lucide-react-native';
import * as React from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import Animated, { FadeInDown, FadeOutDown } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button } from '@/components/app/button';
import { Pulse } from '@/components/app/pulse';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { type Basic, useAddBasics, useBasicImage, useBasics } from '@/lib/basics';
import { CATEGORY_OPTIONS } from '@/lib/garments';
import { selectionFeedback, successFeedback } from '@/lib/haptics';
import { cn } from '@/lib/utils';

const COLUMNS = 3;

function rows<T>(items: T[]): T[][] {
  return Array.from({ length: Math.ceil(items.length / COLUMNS) }, (_, index) =>
    items.slice(index * COLUMNS, index * COLUMNS + COLUMNS)
  );
}

function BasicTile({
  basic,
  selected,
  onToggle,
}: {
  basic: Basic;
  selected: boolean;
  onToggle: () => void;
}) {
  const image = useBasicImage(basic.key);
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: selected }}
      className="flex-1 gap-1.5 active:opacity-80"
      onPress={onToggle}>
      <View
        className={cn(
          'aspect-square overflow-hidden rounded-xl bg-white',
          selected ? 'border-2 border-foreground' : 'border border-border'
        )}>
        <Image source={image} contentFit="cover" style={{ flex: 1 }} transition={150} />
        {selected && (
          <View className="absolute right-1.5 top-1.5 h-6 w-6 items-center justify-center rounded-full bg-primary">
            <Icon as={CheckIcon} size={14} className="text-primary-foreground" />
          </View>
        )}
      </View>
      <Text numberOfLines={2} className="text-sm leading-tight">
        {basic.name}
      </Text>
      {basic.owned && <Text className="text-xs text-muted-foreground">Ya la tienes</Text>}
    </Pressable>
  );
}

function Section({
  label,
  basics,
  selected,
  onToggle,
}: {
  label: string;
  basics: Basic[];
  selected: Set<string>;
  onToggle: (key: string) => void;
}) {
  return (
    <View className="gap-3">
      <Text className="font-sans-medium text-sm text-muted-foreground">{label}</Text>
      {rows(basics).map((row) => (
        <View key={row[0].key} className="flex-row gap-3">
          {row.map((basic) => (
            <BasicTile
              key={basic.key}
              basic={basic}
              selected={selected.has(basic.key)}
              onToggle={() => onToggle(basic.key)}
            />
          ))}
          {/* Empty cells keep the last row's tiles the same width as the others. */}
          {Array.from({ length: COLUMNS - row.length }, (_, index) => (
            <View key={index} className="flex-1" />
          ))}
        </View>
      ))}
    </View>
  );
}

function BasicsSkeleton() {
  return (
    <Pulse style={{ gap: 12 }}>
      {[0, 1].map((row) => (
        <View key={row} className="flex-row gap-3">
          {[0, 1, 2].map((tile) => (
            <View key={tile} className="aspect-square flex-1 rounded-xl bg-muted" />
          ))}
        </View>
      ))}
    </Pulse>
  );
}

// Common items picked from a list: a closet gets going without taking a single photo.
export default function BasicsScreen() {
  const insets = useSafeAreaInsets();
  const { data: basics = [], isLoading } = useBasics();
  const add = useAddBasics();
  const [selected, setSelected] = React.useState<Set<string>>(new Set());

  function toggle(key: string): void {
    selectionFeedback();
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function save(): void {
    add.mutate([...selected], {
      onSuccess: () => {
        successFeedback();
        router.dismissTo('/closet');
      },
    });
  }

  const count = selected.size;

  return (
    <View className="flex-1 bg-background">
      <ScrollView
        contentContainerClassName="gap-6 p-4"
        contentContainerStyle={{ paddingBottom: 120 }}>
        <Text className="text-muted-foreground">
          Toca lo que tienes y lo sumamos a tu armario, sin fotos. Lo demás lo puedes fotografiar
          después.
        </Text>
        {isLoading ? (
          <BasicsSkeleton />
        ) : (
          CATEGORY_OPTIONS.map(({ value, label }) => {
            const inCategory = basics.filter((basic) => basic.category === value);
            return inCategory.length > 0 ? (
              <Section
                key={value}
                label={label}
                basics={inCategory}
                selected={selected}
                onToggle={toggle}
              />
            ) : null;
          })
        )}
      </ScrollView>

      {count > 0 && (
        <Animated.View
          entering={FadeInDown.duration(200)}
          exiting={FadeOutDown.duration(150)}
          className="absolute inset-x-0 bottom-0 gap-2 border-t border-border bg-background px-4 pt-3"
          style={{ paddingBottom: insets.bottom + 12 }}>
          {add.isError && (
            <Text className="text-center text-sm text-destructive">
              No pudimos añadirlas. Inténtalo de nuevo.
            </Text>
          )}
          <Button size="lg" disabled={add.isPending} onPress={save}>
            <Text className="font-sans-semibold">
              {add.isPending
                ? 'Añadiendo…'
                : count === 1
                  ? 'Añadir 1 prenda'
                  : `Añadir ${count} prendas`}
            </Text>
          </Button>
        </Animated.View>
      )}
    </View>
  );
}
