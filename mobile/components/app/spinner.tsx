import { useColorScheme } from 'nativewind';
import { ActivityIndicator, type ActivityIndicatorProps } from 'react-native';

import { THEME } from '@/lib/theme';

// ActivityIndicator takes a color value, not a class, so it reads the theme directly.
export function Spinner(props: ActivityIndicatorProps) {
  const { colorScheme } = useColorScheme();
  return <ActivityIndicator color={THEME[colorScheme ?? 'light'].foreground} {...props} />;
}
