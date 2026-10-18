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
}

const PILLS: PillConfig[] = [
  { id: 'all', label: 'All', icon: Layers },
  { id: 'task', label: 'Task', icon: CheckSquare },
  { id: 'decision', label: 'Decision', icon: Scale },
  { id: 'checkpoint', label: 'Checkpoint', icon: Flag },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen },
  { id: 'agent', label: 'Agent', icon: Bot },
  { id: 'artifact', label: 'Artifact', icon: FileCode },
];

export function MemoryFilterPills({
  activeFilter,
  onChangeFilter,
  counts,
}: MemoryFilterPillsProps) {
  return (
    <div className="relative flex items-center space-x-1.5 p-1 glass-card overflow-x-auto scrollbar-none shadow-sm">
      {PILLS.map((pill) => {
        const Icon = pill.icon;
        const isActive = activeFilter === pill.id;
        const count = counts[pill.id] || 0;

        return (
          <button
            key={pill.id}
            onClick={() => onChangeFilter(pill.id)}
            className={`relative flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 shrink-0 select-none ${
              isActive
                ? 'bg-surface text-text-primary font-semibold shadow-sm border border-border-subtle'
                : 'bg-ice-100 dark:bg-white/[0.06] text-steel-700 dark:text-text-secondary hover:text-text-primary hover:bg-ice-200'
            }`}
          >
            {/* Sliding Magma Underline */}
            {isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red shadow-[0_0_6px_rgba(255,122,26,0.6)]" />
            )}

            <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-lava-orange' : 'text-steel-500'}`} />
            <span>{pill.label}</span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                isActive
                  ? 'bg-ice-100 dark:bg-white/[0.1] text-text-primary font-bold'
                  : 'bg-surface/60 text-text-muted'
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
