import * as React from 'react';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

type OutfitTransitionProps = React.PropsWithChildren<{ outfitId: string; dimmed: boolean }>;

// Dims the outfit while the next one is on its way, then slides the new one in.
export function OutfitTransition({ outfitId, dimmed, children }: OutfitTransitionProps) {
  const appear = useSharedValue(0);
  const dim = useSharedValue(1);

  React.useEffect(() => {
    appear.value = 0;
    appear.value = withTiming(1, { duration: 320, easing: Easing.out(Easing.cubic) });
  }, [outfitId, appear]);

  React.useEffect(() => {
    dim.value = withTiming(dimmed ? 0.35 : 1, { duration: 180 });
  }, [dimmed, dim]);

  const animated = useAnimatedStyle(() => ({
    opacity: appear.value * dim.value,
    transform: [{ translateY: (1 - appear.value) * 14 }],
  }));

  return <Animated.View style={[{ flex: 1, gap: 16 }, animated]}>{children}</Animated.View>;
}
