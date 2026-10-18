import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border-border-subtle',
    secondary: 'bg-ice-200/80 dark:bg-white/[0.04] text-text-secondary border-transparent',
    success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/25',
    warning: 'bg-lava-yellow/15 text-lava-orange dark:text-lava-yellow border-lava-yellow/30 font-medium',
    destructive: 'bg-lava-red/10 text-lava-red dark:text-lava-red border-lava-red/30 font-medium',
    outline: 'text-text-secondary border-border-strong bg-transparent',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-mono font-medium transition-colors',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
