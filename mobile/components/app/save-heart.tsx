import { HeartIcon } from 'lucide-react-native';
import { Pressable } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { THEME } from '@/lib/theme';
import { type Outfit, useSaveOutfit, useUnsaveOutfit } from '@/lib/outfits';

// Sits on the white collage canvas, so it always uses the light theme's ink.
const INK = THEME.light.foreground;

export function SaveHeart({ outfit }: { outfit: Pick<Outfit, 'garments' | 'saved_id'> }) {
  const save = useSaveOutfit();
  const unsave = useUnsaveOutfit();
  const saved = Boolean(outfit.saved_id);

  function toggle(): void {
    if (outfit.saved_id) unsave.mutate(outfit.saved_id);
    else save.mutate(outfit.garments);
  }

  return (
    <Pressable
      accessibilityLabel={saved ? 'Quitar de guardados' : 'Guardar outfit'}
      accessibilityState={{ selected: saved }}
      disabled={save.isPending || unsave.isPending}
      hitSlop={10}
      onPress={toggle}
      className="absolute right-3 top-3 h-11 w-11 items-center justify-center rounded-full bg-white/90 active:opacity-70">
      <Icon as={HeartIcon} size={22} color={INK} fill={saved ? INK : 'transparent'} />
    </Pressable>
  );
}
