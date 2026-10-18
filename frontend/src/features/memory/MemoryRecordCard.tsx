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
        return <CheckSquare className="h-4 w-4 text-ice-400" />;
      case 'decision':
        return <Scale className="h-4 w-4 text-ice-200" />;
      case 'checkpoint':
        return <Flag className="h-4 w-4 text-teal-300" />;
      case 'knowledge':
        return <BookOpen className="h-4 w-4 text-cyan-300" />;
      case 'agent':
        return <Bot className="h-4 w-4 text-amber-400" />;
      case 'artifact':
        return <FileCode className="h-4 w-4 text-rose-400" />;
      default:
        return <FileText className="h-4 w-4 text-ice" />;
    }
  };

  const getRecordTypeBadge = (type: RecordType | 'artifact') => {
    switch (type) {
      case 'task':
        return 'bg-ice-400/15 text-ice-400 border-ice-400/30';
      case 'decision':
        return 'bg-ice-200/15 text-ice-200 border-ice-200/30';
      case 'checkpoint':
        return 'bg-teal-500/15 text-teal-300 border-teal-500/30';
      case 'knowledge':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'agent':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'artifact':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      default:
        return 'bg-secondary text-muted-foreground border-border';
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
      className={`group relative p-3.5 rounded-2xl border transition-all duration-200 cursor-pointer text-left select-none ${
        isSelected
          ? 'bg-ice/10 border-ice/50 shadow-[0_0_20px_rgba(56,189,248,0.2)]'
          : 'bg-card/60 hover:bg-card/90 border-ice/15 hover:border-ice/30 shadow-sm'
      }`}
    >
      {/* Active Left Ice Glow Bar */}
      {isSelected && (
        <span className="absolute left-0 top-3 bottom-3 w-1 bg-ice rounded-r-full shadow-[0_0_8px_rgba(56,189,248,0.9)]" />
      )}

      <div className="flex items-start justify-between gap-2.5">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="p-2 rounded-xl bg-background/60 border border-border/80 shrink-0 group-hover:scale-105 transition-transform">
            {getRecordIcon(record.record_type as any)}
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-bold text-foreground truncate group-hover:text-ice transition-colors">
              {record.title}
            </h4>
            <span className="font-mono text-[10px] text-muted-foreground truncate block">
              {record.record_id}
            </span>
          </div>
        </div>

        <span
          className={`text-[9px] uppercase font-mono px-2 py-0.5 rounded-full border font-bold shrink-0 ${getRecordTypeBadge(
            record.record_type as any
          )}`}
        >
          {record.record_type}
        </span>
      </div>

      {/* Snippet */}
      <p className="text-[11px] text-muted-foreground line-clamp-2 mt-2 leading-relaxed">
        {snippet}
      </p>

      {/* Bottom Metadata: Relative Time, Verification Status */}
      <div className="flex items-center justify-between border-t border-border/40 pt-2.5 mt-2.5 text-[10px]">
        <div className="flex items-center space-x-1.5 text-muted-foreground">
          <Clock className="h-3 w-3 text-muted-foreground/70" />
          <span>{formatDate(record.created_at)}</span>
        </div>

        <div className="flex items-center space-x-2">
          {record.verification_status === 'verified' ? (
            <span className="flex items-center space-x-1 text-emerald-400 font-mono">
              <ShieldCheck className="h-3 w-3" />
              <span>verified</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1 text-amber-400 font-mono">
              <ShieldAlert className="h-3 w-3" />
              <span>{record.verification_status || 'unverified'}</span>
            </span>
          )}

          <ChevronRight
            className={`h-3 w-3 text-muted-foreground transition-transform duration-200 ${
              isSelected ? 'text-ice translate-x-0.5' : 'group-hover:translate-x-0.5'
            }`}
          />
        </div>
      </div>
    </div>
  );
}
