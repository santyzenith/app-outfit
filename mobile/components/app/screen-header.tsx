import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Text } from '@/components/ui/text';

type ScreenHeaderProps = {
  title: string;
  // Small line above the title: the date, a count, a hint.
  eyebrow?: string;
};

// Shared by every tab so they all open with the same title style.
export function ScreenHeader({ title, eyebrow }: ScreenHeaderProps) {
  const insets = useSafeAreaInsets();
  return (
    <View className="px-4 pb-3" style={{ paddingTop: insets.top + 12 }}>
      {eyebrow ? <Text className="text-sm text-muted-foreground">{eyebrow}</Text> : null}
      <Text className="font-serif-medium text-4xl leading-tight">{title}</Text>
    </View>
  );
}
