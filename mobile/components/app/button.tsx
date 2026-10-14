import * as React from 'react';

import { Button as BaseButton } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type ButtonProps = React.ComponentProps<typeof BaseButton>;

// Material 3 pill shape everywhere; large buttons get the 48dp touch target.
const SHAPE: Record<NonNullable<ButtonProps['size']>, string> = {
  default: 'h-11 rounded-full px-5',
  sm: 'h-9 rounded-full px-3',
  lg: 'h-12 rounded-full px-6',
  icon: 'h-11 w-11 rounded-full',
};

export function Button({ size, className, ...props }: ButtonProps) {
  return <BaseButton size={size} className={cn(SHAPE[size ?? 'default'], className)} {...props} />;
}
