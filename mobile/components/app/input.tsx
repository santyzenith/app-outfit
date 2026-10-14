import * as React from 'react';

import { Input as BaseInput } from '@/components/ui/input';
import { cn } from '@/lib/utils';

type InputProps = React.ComponentProps<typeof BaseInput>;

// Text inputs don't inherit the app font, so it's set here along with the shared shape.
export function Input({ className, multiline, ...props }: InputProps) {
  return (
    <BaseInput
      multiline={multiline}
      className={cn('h-12 rounded-xl px-4 font-sans', multiline && 'h-24 py-3', className)}
      {...props}
    />
  );
}
