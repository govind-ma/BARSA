import React from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading = false, disabled, children, ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-steel-500 dark:focus-visible:ring-lava-yellow disabled:opacity-50 disabled:pointer-events-none rounded-[8px] select-none';

    const variants = {
      primary:
        'btn-magma text-[#0C0A0B] font-semibold active:scale-[0.97]',
      secondary:
        'btn-secondary-ice active:scale-[0.98]',
      outline:
        'border border-border-strong bg-surface/70 hover:bg-ice-200/60 dark:hover:bg-white/[0.1] text-text-primary active:scale-[0.98]',
      ghost:
        'hover:bg-ice-100 dark:hover:bg-white/[0.06] text-text-secondary hover:text-text-primary active:scale-[0.98]',
      destructive:
        'bg-lava-red hover:bg-lava-deep text-white shadow-sm hover:shadow-[0_0_15px_rgba(229,48,31,0.4)] active:scale-[0.97]',
    };

    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-9 px-4 py-2 text-sm',
      lg: 'h-10 px-6 text-base',
      icon: 'h-9 w-9 p-0',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin shrink-0" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
