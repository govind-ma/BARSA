import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
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
      {/* Lava-red-bordered Alert Banner at Top with Pulsing Dot */}
      <div className="w-full rounded-xl border border-lava-red/40 bg-lava-red/10 backdrop-blur-md p-4 shadow-md transition-all animate-page-enter mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {/* Pulsing Lava Dot */}
            <div className="relative flex items-center justify-center">
              <span className="h-3 w-3 rounded-full bg-lava-red animate-ping absolute opacity-75" />
              <span className="h-2.5 w-2.5 rounded-full bg-lava-red shadow-[0_0_8px_rgba(229,48,31,0.9)]" />
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <h4 className="font-heading text-sm font-semibold text-lava-red tracking-tight">
                  Merge Conflicts Detected
                </h4>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-lava-red/20 text-lava-red border border-lava-red/30 font-bold">
                  {conflicts.length} Unresolved
                </span>
              </div>
              <p className="text-xs text-text-secondary mt-0.5">
                Divergent field modifications across concurrent agent commits require manual adjudication.
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsExpanded((prev) => !prev)}
            className="p-1.5 rounded-lg text-lava-red hover:bg-lava-red/20 transition-colors"
            title={isExpanded ? 'Collapse panel' : 'Expand panel'}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>

        {/* Expanded Panel with 3 resolution options per conflict */}
        {isExpanded && (
          <div className="mt-4 pt-3 border-t border-lava-red/20 space-y-3 animate-page-enter">
            {conflicts.map((conf) => (
              <div
                key={`${conf.record_id}-${conf.field_name}`}
                className="p-3.5 rounded-lg bg-surface border border-border-subtle shadow-sm space-y-3"
              >
                {/* Conflict identifier header (satisfies test expecting "Conflict in") */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-border-subtle pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-heading text-xs font-semibold text-text-primary">
                      Conflict in {conf.record_id}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary font-semibold">
                      field: {conf.field_name}
                    </span>
                  </div>

                  <span className="text-[10px] font-mono text-lava-red font-semibold">
                    {conf.is_resolved ? 'Resolved' : 'Pending Action'}
                  </span>
                </div>

                {/* 3 Values: Base, Source (A), Target (B) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-xs font-mono">
                  {/* Base Value */}
                  <div className="p-2.5 rounded-lg bg-surface/70 border border-border-subtle space-y-1">
                    <span className="text-[10px] uppercase font-bold text-text-muted block">
                      Base Value
                    </span>
                    <p className="text-[11px] text-text-secondary break-words">
                      {conf.base_value ? String(conf.base_value) : '(empty)'}
                    </p>
                  </div>

                  {/* Source Value (A) */}
                  <div className="p-2.5 rounded-lg bg-ice-100 dark:bg-white/[0.06] border border-border-subtle space-y-1">
                    <span className="text-[10px] uppercase font-bold text-steel-700 dark:text-text-primary block">
                      Source (Branch)
                    </span>
                    <p className="text-[11px] text-text-primary break-words font-medium">
                      {conf.source_value ? String(conf.source_value) : '(empty)'}
                    </p>
                  </div>

                  {/* Target Value (B) */}
                  <div className="p-2.5 rounded-lg bg-lava-yellow/15 border border-lava-yellow/30 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-lava-orange block">
                      Target (Main)
                    </span>
                    <p className="text-[11px] text-lava-orange dark:text-lava-yellow break-words font-medium">
                      {conf.target_value ? String(conf.target_value) : '(empty)'}
                    </p>
                  </div>
                </div>

                {/* Action Buttons: Take A, Take B, 3-way merge */}
                <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-border-subtle">
                  <button
                    onClick={() =>
                      onResolveConflict(
                        conf.record_id,
                        conf.field_name,
                        conf.source_value,
                        'Take A'
                      )
                    }
                    className="px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium"
                  >
                    Take A
                  </button>

                  <button
                    onClick={() =>
                      onResolveConflict(
                        conf.record_id,
                        conf.field_name,
                        conf.target_value,
                        'Take B'
                      )
                    }
                    className="px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium"
                  >
                    Take B
                  </button>

                  <button
                    onClick={() => handleOpen3Way(conf)}
                    className="inline-flex items-center space-x-1 px-3.5 py-1.5 rounded-lg btn-magma text-xs font-semibold shadow-sm"
                  >
                    <GitMerge className="h-3.5 w-3.5" />
                    <span>3-way merge</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3-way Merge Editor Modal */}
      <Modal
        isOpen={!!mergeModalConflict}
        onClose={() => setMergeModalConflict(null)}
        title={`3-Way Merge Editor: ${mergeModalConflict?.record_id} (${mergeModalConflict?.field_name})`}
        className="max-w-xl"
      >
        <div className="space-y-4 pt-2 text-xs">
          <p className="text-text-secondary leading-relaxed">
            Synthesize divergent updates from both agent commits into an authoritative resolution.
          </p>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block">
              Resolved Output Value
            </label>
            <Textarea
              value={customMergedValue}
              onChange={(e) => setCustomMergedValue(e.target.value)}
              rows={8}
              className="font-mono text-xs bg-bg-base border-border-subtle"
            />
          </div>

          <div className="pt-2 flex justify-end space-x-2 border-t border-border-subtle">
            <button
              onClick={() => setMergeModalConflict(null)}
              className="px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSave3WayMerge}
              className="px-4 py-1.5 rounded-lg btn-magma text-xs font-semibold shadow-sm"
            >
              Apply Merge Resolution
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
