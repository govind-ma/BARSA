import {
  CheckSquare,
  Scale,
  Flag,
  BookOpen,
  Bot,
  FileCode,
  FileText,
  Clock,
  ShieldCheck,
  ShieldAlert,
  ChevronRight,
} from 'lucide-react';
import type { BMSRecord, RecordType } from '@/types';
import { formatDate } from '@/lib/utils';

interface MemoryRecordCardProps {
  record: BMSRecord;
  isSelected: boolean;
  onClick: () => void;
}

export function MemoryRecordCard({
  record,
  isSelected,
  onClick,
}: MemoryRecordCardProps) {
  const getRecordIcon = (type: RecordType | 'artifact') => {
    switch (type) {
      case 'task':
        return <CheckSquare className="h-4 w-4 text-steel-500" />;
      case 'decision':
        return <Scale className="h-4 w-4 text-lava-yellow" />;
      case 'checkpoint':
        return <Flag className="h-4 w-4 text-steel-700 dark:text-text-primary" />;
      case 'knowledge':
        return <BookOpen className="h-4 w-4 text-steel-500" />;
      case 'agent':
        return <Bot className="h-4 w-4 text-lava-orange" />;
      case 'artifact':
        return <FileCode className="h-4 w-4 text-steel-700 dark:text-text-secondary" />;
      default:
        return <FileText className="h-4 w-4 text-steel-500" />;
    }
  };

  const getRecordTypeBadge = (type: RecordType | 'artifact') => {
    switch (type) {
      case 'task':
        return 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border-border-subtle';
      case 'decision':
        return 'bg-lava-yellow/15 text-lava-orange dark:text-lava-yellow border-lava-yellow/30 font-medium';
      case 'checkpoint':
        return 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary border-border-subtle';
      case 'knowledge':
        return 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary border-border-subtle';
      case 'agent':
        return 'bg-lava-orange/15 text-lava-orange border-lava-orange/30 font-medium';
      case 'artifact':
        return 'bg-ice-200 dark:bg-white/[0.1] text-steel-700 dark:text-text-primary border-border-subtle';
      default:
        return 'bg-ice-100 text-text-muted border-border-subtle';
    }
  };

  const snippet = record.summary || record.content || 'No details provided';

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={`group relative p-3.5 rounded-lg border transition-all duration-200 cursor-pointer text-left select-none ${
        isSelected
          ? 'bg-surface border-border-strong shadow-md ring-1 ring-steel-500/30'
          : 'bg-surface/80 hover:bg-surface border-border-subtle hover:border-border-strong hover:-translate-y-0.5 shadow-sm'
      }`}
    >
      {/* Active Left Magma Bar */}
      {isSelected && (
        <span className="absolute left-0 top-3 bottom-3 w-1 rounded-r-full bg-gradient-to-b from-lava-yellow via-lava-orange to-lava-red shadow-[0_0_8px_rgba(255,122,26,0.5)]" />
      )}

      <div className="flex items-start justify-between gap-2.5">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="p-2 rounded-lg bg-surface border border-border-subtle shrink-0 group-hover:scale-105 transition-transform shadow-sm">
            {getRecordIcon(record.record_type as any)}
          </div>
          <div className="min-w-0">
            <h4 className="font-heading text-xs font-semibold text-text-primary truncate group-hover:text-lava-orange transition-colors">
              {record.title}
            </h4>
            <span className="font-mono text-[10px] text-text-muted truncate block">
              {record.record_id}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 shrink-0">
          {record.verification_status === 'verified' ? (
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <ShieldAlert className="h-3.5 w-3.5 text-text-muted" />
          )}
          <span
            className={`text-[9px] uppercase font-mono px-2 py-0.5 rounded-md border font-semibold ${getRecordTypeBadge(
              record.record_type as any
            )}`}
          >
            {record.record_type}
          </span>
        </div>
      </div>

      {/* Snippet */}
      <p className="mt-2 text-xs text-text-secondary line-clamp-2 leading-relaxed">
        {snippet}
      </p>

      {/* Footer Info */}
      <div className="mt-2.5 pt-2 border-t border-border-subtle flex items-center justify-between text-[10px] text-text-muted">
        <div className="flex items-center space-x-1 font-mono">
          <Clock className="h-3 w-3 text-steel-500" />
          <span>{formatDate(record.created_at)}</span>
        </div>

        <div className="flex items-center space-x-1 group-hover:text-text-primary transition-colors">
          <span className="font-mono text-[10px]">{record.author}</span>
          <ChevronRight className="h-3 w-3 opacity-60 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </div>
    </div>
  );
}
