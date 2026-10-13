import * as React from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

type PulseProps = React.PropsWithChildren<{ style?: StyleProp<ViewStyle> }>;

// Breathing placeholder: wraps the grey shapes shown while real content loads.
export function Pulse({ style, children }: PulseProps) {
  const opacity = useSharedValue(1);

  React.useEffect(() => {
    opacity.value = withRepeat(withTiming(0.45, { duration: 800 }), -1, true);
  }, [opacity]);

  const animated = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return <Animated.View style={[style, animated]}>{children}</Animated.View>;
}
