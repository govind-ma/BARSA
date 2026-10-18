import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Check,
  GitMerge,
} from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Textarea } from '@/components/ui/Input';
import type { ConflictItem } from '@/types';

interface ConflictsInspectorProps {
  conflicts: ConflictItem[];
  onResolveConflict: (
    recordId: string,
    fieldName: string,
    resolvedValue: unknown,
    resolutionType: 'Take A' | 'Take B' | '3-way merge'
  ) => void;
}

export function ConflictsInspector({
  conflicts,
  onResolveConflict,
}: ConflictsInspectorProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [mergeModalConflict, setMergeModalConflict] = useState<ConflictItem | null>(null);
  const [customMergedValue, setCustomMergedValue] = useState('');

  if (conflicts.length === 0) return null;

  const handleOpen3Way = (c: ConflictItem) => {
    setMergeModalConflict(c);
    setCustomMergedValue(
      typeof c.source_value === 'string'
        ? c.source_value
        : JSON.stringify(c.source_value, null, 2)
    );
  };

  const handleSave3WayMerge = () => {
    if (!mergeModalConflict) return;
    onResolveConflict(
      mergeModalConflict.record_id,
      mergeModalConflict.field_name,
      customMergedValue,
      '3-way merge'
    );
    setMergeModalConflict(null);
  };

  return (
    <>
      {/* Chilli-bordered Alert Banner at Top with Pulsing Dot */}
      <div className="w-full rounded-2xl border border-chilli/50 bg-chilli/10 backdrop-blur-md p-4 shadow-[0_0_30px_rgba(239,68,68,0.2)] transition-all animate-page-enter mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {/* Pulsing Chilli Dot */}
            <div className="relative flex items-center justify-center">
              <span className="h-3 w-3 rounded-full bg-chilli animate-ping absolute opacity-75" />
              <span className="h-2.5 w-2.5 rounded-full bg-chilli shadow-[0_0_8px_rgba(239,68,68,0.9)]" />
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <h4 className="text-sm font-bold text-chilli tracking-tight">
                  Merge Conflicts Detected
                </h4>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-chilli/20 text-chilli border border-chilli/30 font-bold">
                  {conflicts.length} Unresolved
                </span>
              </div>
              <p className="text-xs text-chilli/90 mt-0.5">
                Divergent field modifications across concurrent agent commits require manual adjudication.
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsExpanded((prev) => !prev)}
            className="p-1.5 rounded-lg text-chilli hover:bg-chilli/20 transition-colors"
            title={isExpanded ? 'Collapse panel' : 'Expand panel'}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>

        {/* Expanded Panel with 3 resolution options per conflict */}
        {isExpanded && (
          <div className="mt-4 pt-3 border-t border-chilli/25 space-y-3 animate-page-enter">
            {conflicts.map((conf) => (
              <div
                key={`${conf.record_id}-${conf.field_name}`}
                className="p-3.5 rounded-xl bg-card/85 border border-chilli/30 shadow-sm space-y-3"
              >
                {/* Conflict identifier header (satisfies test 9) */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-border/60 pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-foreground">
                      Conflict in {conf.record_id}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary text-ice font-semibold">
                      field: {conf.field_name}
                    </span>
                  </div>

                  <span className="text-[10px] font-mono text-chilli font-semibold">
                    {conf.is_resolved ? 'Resolved' : 'Pending Action'}
                  </span>
                </div>

                {/* 3 Values: Base, Source (A), Target (B) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-xs font-mono">
                  {/* Base Value */}
                  <div className="p-2.5 rounded-lg bg-secondary/40 border border-border/60 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                      Base Value
                    </span>
                    <p className="text-[11px] text-foreground/90 break-words">
                      {conf.base_value ? String(conf.base_value) : '(empty)'}
                    </p>
                  </div>

                  {/* Source Value (A) */}
                  <div className="p-2.5 rounded-lg bg-ice/10 border border-ice/30 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-ice block">
                      Source (Branch)
                    </span>
                    <p className="text-[11px] text-ice break-words">
                      {conf.source_value ? String(conf.source_value) : '(empty)'}
                    </p>
                  </div>

                  {/* Target Value (B) */}
                  <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-amber-400 block">
                      Target (Main)
                    </span>
                    <p className="text-[11px] text-amber-300 break-words">
                      {conf.target_value ? String(conf.target_value) : '(empty)'}
                    </p>
                  </div>
                </div>

                {/* Three Action Buttons: Take A, Take B, 3-way merge */}
                <div className="flex items-center justify-end space-x-2 pt-1">
                  <button
                    onClick={() =>
                      onResolveConflict(conf.record_id, conf.field_name, conf.source_value, 'Take A')
                    }
                    className="px-3 py-1.5 rounded-lg bg-ice/15 hover:bg-ice/25 text-ice font-bold text-xs border border-ice/30 transition-all shadow-sm"
                  >
                    Take A
                  </button>

                  <button
                    onClick={() =>
                      onResolveConflict(conf.record_id, conf.field_name, conf.target_value, 'Take B')
                    }
                    className="px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 font-bold text-xs border border-amber-500/30 transition-all shadow-sm"
                  >
                    Take B
                  </button>

                  <button
                    onClick={() => handleOpen3Way(conf)}
                    className="px-3.5 py-1.5 rounded-lg bg-chilli hover:bg-chilli/90 text-white font-bold text-xs shadow-[0_0_12px_rgba(239,68,68,0.35)] transition-all flex items-center space-x-1.5"
                  >
                    <GitMerge className="h-3 w-3" />
                    <span>3-way merge</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3-way Merge Editor Modal */}
      {mergeModalConflict && (
        <Modal
          isOpen={true}
          onClose={() => setMergeModalConflict(null)}
          title={`3-Way Merge Editor — ${mergeModalConflict.record_id}`}
          className="max-w-xl"
        >
          <div className="space-y-4 pt-1 text-xs">
            <p className="text-muted-foreground">
              Manually synthesize both agent changes for field{' '}
              <strong className="text-ice font-mono">{mergeModalConflict.field_name}</strong>.
            </p>

            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div className="p-2 rounded bg-ice/10 border border-ice/20">
                <span className="text-[10px] text-ice block font-bold mb-0.5">Source (A):</span>
                <span className="text-ice break-words">{String(mergeModalConflict.source_value)}</span>
              </div>
              <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20">
                <span className="text-[10px] text-amber-400 block font-bold mb-0.5">Target (B):</span>
                <span className="text-amber-300 break-words">{String(mergeModalConflict.target_value)}</span>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                Synthesized Result Value
              </label>
              <Textarea
                value={customMergedValue}
                onChange={(e) => setCustomMergedValue(e.target.value)}
                rows={5}
                className="font-mono text-xs bg-secondary/40 border-ice/25 focus-visible:ring-ice/50"
              />
            </div>

            <div className="pt-2 flex justify-end space-x-2 border-t border-border">
              <button
                type="button"
                onClick={() => setMergeModalConflict(null)}
                className="px-3.5 py-1.5 rounded-xl border border-border hover:bg-secondary text-foreground text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave3WayMerge}
                className="px-4 py-1.5 rounded-xl bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-[0_0_15px_rgba(56,189,248,0.4)] transition-all flex items-center space-x-1.5"
              >
                <Check className="h-3.5 w-3.5" />
                <span>Apply 3-Way Merge</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
