import * as React from 'react';
import {
  type GestureResponderEvent,
  Pressable,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';

import { selectionFeedback } from '@/lib/haptics';

type TabButtonProps = Omit<PressableProps, 'style' | 'children' | 'onPress'> & {
  style?: StyleProp<ViewStyle>;
  children: React.ReactNode;
  onPress?: (event: GestureResponderEvent) => void;
};

// Replaces Android's ripple on the tab bar: the icon dips slightly and the phone ticks.
export function TabButton({
  style,
  children,
  onPressIn,
  onPressOut,
  onPress,
  ...rest
}: TabButtonProps) {
  const scale = useSharedValue(1);
  const press = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const selected = rest.accessibilityState?.selected ?? rest['aria-selected'];

  return (
    <Pressable
      {...rest}
      android_ripple={null}
      style={{ flex: 1 }}
      onPressIn={(event) => {
        scale.value = withTiming(0.86, { duration: 90 });
        onPressIn?.(event);
      }}
      onPressOut={(event) => {
        scale.value = withSpring(1, { damping: 12, stiffness: 260 });
        onPressOut?.(event);
      }}
      onPress={(event) => {
        if (!selected) selectionFeedback();
        onPress?.(event);
      }}>
      <Animated.View style={[style, press]}>{children}</Animated.View>
    </Pressable>
  );
}
