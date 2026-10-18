import React from 'react';
import { cn } from '@/lib/utils';
import { Inbox } from 'lucide-react';
import { Button } from './Button';
import { EmberSparks } from './EmberSparks';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
  showSparks?: boolean;
}

export function EmptyState({
  icon = <Inbox className="h-10 w-10 text-steel-500" />,
  title,
  description,
  actionLabel,
  onAction,
  className,
  showSparks = true,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden flex min-h-[260px] flex-col items-center justify-center rounded-xl border border-dashed border-border-strong bg-surface/50 p-10 text-center animate-in fade-in duration-200',
        className
      )}
    >
      {showSparks && <EmberSparks count={4} />}

      <div className="relative z-10 flex h-12 w-12 items-center justify-center rounded-xl bg-ice-100 dark:bg-white/[0.08] border border-border-subtle mb-3 text-steel-500 shadow-sm">
        {icon}
      </div>
      <h3 className="relative z-10 font-heading text-sm font-semibold text-text-primary">{title}</h3>
      <p className="relative z-10 mt-1 max-w-sm text-xs text-text-secondary">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} className="relative z-10 mt-4" size="sm" variant="secondary">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

export function LoadingSpinner({ text = 'Loading data...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] space-y-3">
      <div className="h-7 w-7 animate-spin rounded-full border-2 border-lava-orange border-t-transparent shadow-[0_0_12px_rgba(255,122,26,0.4)]" />
      <span className="text-xs text-text-muted font-mono">{text}</span>
    </div>
  );
}
