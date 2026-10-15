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
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none rounded-lg active:scale-[0.98]';

    const variants = {
      primary: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:shadow',
      secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      outline: 'border border-border/80 bg-card/60 hover:bg-accent/80 hover:text-accent-foreground text-foreground',
      ghost: 'hover:bg-accent/70 hover:text-accent-foreground text-muted-foreground hover:text-foreground',
      destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm',
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
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
