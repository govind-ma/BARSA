import React from 'react';
import { cn } from '@/lib/utils';
import { Inbox } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon = <Inbox className="h-10 w-10 text-muted-foreground" />,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex min-h-[260px] flex-col items-center justify-center rounded-2xl border border-dashed border-border/80 bg-card/30 p-10 text-center animate-in fade-in',
        className
      )}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50 border border-border/60 mb-4 text-muted-foreground">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} className="mt-5" size="sm">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

export function LoadingSpinner({ text = 'Loading data...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] space-y-3">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      <span className="text-xs text-muted-foreground">{text}</span>
    </div>
  );
}
