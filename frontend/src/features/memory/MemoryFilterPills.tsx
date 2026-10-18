import {
  Layers,
  CheckSquare,
  Scale,
  Flag,
  BookOpen,
  Bot,
  FileCode,
} from 'lucide-react';

export type MemoryFilterType =
  | 'all'
  | 'task'
  | 'decision'
  | 'checkpoint'
  | 'knowledge'
  | 'agent'
  | 'artifact';

interface MemoryFilterPillsProps {
  activeFilter: MemoryFilterType;
  onChangeFilter: (filter: MemoryFilterType) => void;
  counts: Record<MemoryFilterType, number>;
}

interface PillConfig {
  id: MemoryFilterType;
  label: string;
  icon: typeof Layers;
  colorClass: string;
}

const PILLS: PillConfig[] = [
  { id: 'all', label: 'All', icon: Layers, colorClass: 'text-ice' },
  { id: 'task', label: 'Task', icon: CheckSquare, colorClass: 'text-ice-400' },
  { id: 'decision', label: 'Decision', icon: Scale, colorClass: 'text-ice-200' },
  { id: 'checkpoint', label: 'Checkpoint', icon: Flag, colorClass: 'text-teal-300' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, colorClass: 'text-cyan-300' },
  { id: 'agent', label: 'Agent', icon: Bot, colorClass: 'text-amber-400' },
  { id: 'artifact', label: 'Artifact', icon: FileCode, colorClass: 'text-rose-400' },
];

export function MemoryFilterPills({
  activeFilter,
  onChangeFilter,
  counts,
}: MemoryFilterPillsProps) {
  return (
    <div className="relative flex items-center space-x-1 p-1 bg-card/60 backdrop-blur-md border border-ice/15 rounded-2xl overflow-x-auto scrollbar-none shadow-sm">
      {PILLS.map((pill) => {
        const Icon = pill.icon;
        const isActive = activeFilter === pill.id;
        const count = counts[pill.id] || 0;

        return (
          <button
            key={pill.id}
            onClick={() => onChangeFilter(pill.id)}
            className={`relative flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 shrink-0 select-none ${
              isActive
                ? 'bg-ice/15 text-ice border border-ice/35 shadow-[0_0_12px_rgba(56,189,248,0.25)] font-bold'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40 border border-transparent'
            }`}
          >
            {/* Sliding Ice Indicator Pill Bar */}
            {isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-ice rounded-full shadow-[0_0_8px_rgba(56,189,248,0.9)] animate-pulse" />
            )}

            <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-ice' : pill.colorClass}`} />
            <span>{pill.label}</span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                isActive
                  ? 'bg-ice/25 text-ice font-bold'
                  : 'bg-secondary/60 text-muted-foreground'
              }`}
            >
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
