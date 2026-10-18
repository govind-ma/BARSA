import { useState } from 'react';
import {
  Copy,
  Check,
  ArrowRight,
  BookmarkCheck,
  AlertTriangle,
  Bot,
  GitCommit,
  Clock,
  Layers,
  ArrowLeft,
  FileCode,
  X,
} from 'lucide-react';
import { formatDate, truncate } from '@/lib/utils';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import type { GraphNode, GraphEdge, BMSRecord, CoordinationTask } from '@/types';

interface ActiveStateHandoverProps {
  selectedNode: GraphNode | null;
  onClearSelectedNode: () => void;
  activeTask?: CoordinationTask | null;
  lastCheckpoint?: BMSRecord | null;
  whyReadyText?: string;
  projectName: string;
  allEdges: GraphEdge[];
  onTriggerToast: (msg: string) => void;
  fullContextPrompt?: string;
}

export function ActiveStateHandover({
  selectedNode,
  onClearSelectedNode,
  activeTask,
  lastCheckpoint,
  whyReadyText,
  projectName,
  allEdges,
  onTriggerToast,
  fullContextPrompt,
}: ActiveStateHandoverProps) {
  const [isCopiedPrompt, setIsCopiedPrompt] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCopiedContext, setIsCopiedContext] = useState(false);

  // Compute Inbound & Outbound relationships if a node is selected
  const nodeRelationships = selectedNode
    ? {
        inbound: allEdges.filter((e) => e.target === selectedNode.id),
        outbound: allEdges.filter((e) => e.source === selectedNode.id),
      }
    : null;

  // Handover prompt generator
  const nextActionText =
    (lastCheckpoint?.attributes as any)?.next_action ||
    whyReadyText ||
    'Inspect verified FalkorDB dependencies and proceed with implementation';

  const generatedPrompt =
    fullContextPrompt ||
    `[BARSA Universal AI Handover Protocol v0.2 - Ice & Lava]
Project: ${projectName}
Active Task: ${activeTask?.task_id || 'TASK-NEXT'} (${activeTask?.title || 'Execution phase'})
Next Action: ${nextActionText}
Latest Checkpoint: ${lastCheckpoint?.record_id || (lastCheckpoint as any)?.id || 'rec_cp_01'}
Base Commit: ${(lastCheckpoint?.attributes as any)?.base_revision || 'head'}
Instruction: Resume work seamlessly without losing context. All prior ADRs and commits are locked in local BMS memory.`;

  const handleCopyHandoverPrompt = () => {
    navigator.clipboard.writeText(generatedPrompt);
    setIsCopiedPrompt(true);
    onTriggerToast('Context copied. Paste it into your next agent.');
    setTimeout(() => setIsCopiedPrompt(false), 2000);
  };

  const handleCopyFullContext = () => {
    navigator.clipboard.writeText(generatedPrompt);
    setIsCopiedContext(true);
    onTriggerToast('Full context package copied to clipboard.');
    setTimeout(() => setIsCopiedContext(false), 2000);
  };

  // If a node is selected in the knowledge graph, render Node Detail view
  if (selectedNode) {
    const cypherSnippet = `MATCH (n {id: "${selectedNode.id}"})-[r]-(target)\nRETURN n, r, target;`;

    return (
      <div className="flex flex-col h-full glass-card p-4 shadow-md select-none animate-page-enter">
        {/* Back Button */}
        <button
          onClick={onClearSelectedNode}
          className="inline-flex items-center space-x-1.5 text-xs text-steel-700 dark:text-text-primary hover:text-lava-orange font-medium mb-3 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Active Task</span>
        </button>

        {/* Node Detail Header */}
        <div className="pb-3 border-b border-border-subtle mb-3">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-text-primary border border-border-subtle font-mono font-bold uppercase">
              {selectedNode.type || 'Entity'}
            </span>
            <span className="text-xs font-mono text-text-muted truncate">
              {selectedNode.id}
            </span>
          </div>
          <h3 className="font-heading text-base font-semibold text-text-primary tracking-tight">
            {selectedNode.label || selectedNode.id}
          </h3>
        </div>

        {/* Scrollable details */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4 text-xs">
          {/* Properties */}
          <div>
            <h4 className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-bold mb-1.5">
              Properties
            </h4>
            <div className="bg-surface/80 rounded-lg p-2.5 border border-border-subtle space-y-1 font-mono text-[11px]">
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 ? (
                Object.entries(selectedNode.properties).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-text-muted">{k}:</span>
                    <span className="text-text-primary truncate">{String(v)}</span>
                  </div>
                ))
              ) : (
                <div className="text-text-muted italic">No extra properties</div>
              )}
            </div>
          </div>

          {/* Relationships */}
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 rounded-lg bg-surface/70 border border-border-subtle">
              <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                Inbound ({nodeRelationships?.inbound.length || 0})
              </span>
              <div className="space-y-1">
                {nodeRelationships?.inbound.slice(0, 3).map((edge, i) => (
                  <div key={i} className="text-[10px] font-mono text-text-secondary truncate">
                    &larr; {edge.type} ({edge.source})
                  </div>
                ))}
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-surface/70 border border-border-subtle">
              <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                Outbound ({nodeRelationships?.outbound.length || 0})
              </span>
              <div className="space-y-1">
                {nodeRelationships?.outbound.slice(0, 3).map((edge, i) => (
                  <div key={i} className="text-[10px] font-mono text-text-secondary truncate">
                    &rarr; {edge.type} ({edge.target})
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Cypher Query Snippet */}
          <div>
            <h4 className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-bold mb-1.5">
              FalkorDB Cypher Path
            </h4>
            <pre className="p-2.5 rounded-lg bg-bg-base border border-border-subtle font-mono text-[10px] text-text-primary overflow-x-auto select-text">
              {cypherSnippet}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Default view: Active State & Handover
  return (
    <>
      <div className="flex flex-col h-full glass-card p-3.5 shadow-md select-none">
        {/* Pane Header */}
        <div className="flex items-center justify-between pb-3 mb-2 border-b border-border-subtle">
          <div className="flex items-center space-x-2">
            <div className="h-6 w-6 rounded-md bg-ice-100 dark:bg-white/[0.08] border border-border-subtle flex items-center justify-center text-steel-700 dark:text-text-primary">
              <Layers className="h-3.5 w-3.5" />
            </div>
            <div>
              <h3 className="font-heading text-xs font-semibold tracking-tight text-text-primary uppercase">
                Active State & Handover
              </h3>
              <span className="text-[10px] text-text-muted block -mt-0.5 font-mono">
                Zero-cloud synchronization
              </span>
            </div>
          </div>

          <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/25 font-mono font-medium">
            Ready
          </span>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-3.5">
          {/* Active Task Card */}
          <div className="p-3.5 rounded-lg bg-surface border border-border-subtle shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-steel-700 dark:text-text-primary px-2 py-0.5 rounded bg-ice-100 dark:bg-white/[0.08] border border-border-subtle">
                {activeTask?.task_id || 'TASK-RECOMMENDED'}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-lava-yellow/15 text-lava-orange dark:text-lava-yellow border border-lava-yellow/30 font-semibold uppercase">
                {activeTask?.priority || 'High'}
              </span>
            </div>

            <h4 className="font-heading text-xs font-semibold text-text-primary leading-snug">
              {activeTask?.title || 'FalkorDB Multi-Agent Coordination Pipeline'}
            </h4>

            <div className="flex items-center justify-between text-[11px] text-text-muted pt-1 border-t border-border-subtle font-mono">
              <span>Dependencies: {activeTask?.dependencies?.length ?? 2} satisfied</span>
              {activeTask?.blockers && activeTask.blockers.length > 0 ? (
                <span className="text-lava-red flex items-center space-x-1 font-semibold">
                  <AlertTriangle className="h-3 w-3" />
                  <span>{activeTask.blockers.length} Blocker</span>
                </span>
              ) : (
                <span className="text-emerald-700 dark:text-emerald-400">0 Blockers</span>
              )}
            </div>
          </div>

          {/* Next Action Callout (Large, left border in --magma, white card, larger text) */}
          <div className="next-action-callout p-3.5 rounded-r-lg bg-surface border-y border-r border-border-subtle shadow-sm space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[10px] font-mono font-bold uppercase text-lava-orange tracking-wider">
              <ArrowRight className="h-3 w-3 text-lava-orange" />
              <span>Next Action Callout</span>
            </div>
            <p className="font-heading text-sm text-text-primary font-medium leading-relaxed">
              {nextActionText}
            </p>
          </div>

          {/* Last Checkpoint Card */}
          <div className="p-3 rounded-lg bg-surface/70 border border-border-subtle space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase font-bold text-text-muted flex items-center space-x-1">
                <BookmarkCheck className="h-3 w-3 text-steel-500" />
                <span>Last Checkpoint</span>
              </span>
              <span className="font-mono text-[10px] text-text-primary font-bold">
                {truncate(lastCheckpoint?.record_id || (lastCheckpoint as any)?.id || 'rec_cp_init', 12)}
              </span>
            </div>

            <div className="flex justify-between text-[11px] text-text-secondary">
              <span className="flex items-center space-x-1">
                <Bot className="h-3 w-3 text-steel-500" />
                <span>{lastCheckpoint?.author || 'claude-architect'}</span>
              </span>
              <span className="flex items-center space-x-1">
                <Clock className="h-3 w-3 text-steel-500" />
                <span>{formatDate(lastCheckpoint?.created_at || new Date().toISOString())}</span>
              </span>
            </div>

            <div className="flex items-center space-x-1 font-mono text-[10px] text-text-muted pt-1 border-t border-border-subtle">
              <GitCommit className="h-3 w-3" />
              <span>Base: {truncate((lastCheckpoint?.attributes as any)?.base_revision || 'head', 10)}</span>
            </div>
          </div>
        </div>

        {/* Bottom Actions - Clear primary magma button with visible label & icon! */}
        <div className="pt-3 border-t border-border-subtle space-y-2 mt-2">
          {/* Primary Button: Copy handover prompt */}
          <button
            onClick={handleCopyHandoverPrompt}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg btn-magma text-xs font-semibold shadow-md active:scale-[0.97]"
            title="Copies full continuation prompt for ChatGPT, Claude, or Cursor"
          >
            {isCopiedPrompt ? (
              <>
                <Check className="h-4 w-4" />
                <span>Context Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span>Copy handover prompt</span>
              </>
            )}
          </button>

          {/* Secondary Button: View full context */}
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="w-full flex items-center justify-center space-x-2 py-2 px-4 rounded-lg btn-secondary-ice text-xs font-medium"
          >
            <FileCode className="h-3.5 w-3.5 text-steel-500" />
            <span>View full context</span>
          </button>
        </div>
      </div>

      {/* Right Drawer: Compressed Token-Optimized Prompt */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm animate-page-enter">
          <div className="w-full max-w-lg h-full bg-surface border-l border-border-subtle p-6 flex flex-col justify-between shadow-2xl">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
                <div className="flex items-center space-x-2">
                  <BarsaLogo size={20} />
                  <h3 className="font-heading text-sm font-semibold text-text-primary">
                    Compressed Smart Context Package
                  </h3>
                </div>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-ice-100"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-center space-x-3 text-xs text-text-muted font-mono">
                <span>Tokens: ~420</span>
                <span>•</span>
                <span>Standard: BMS v0.2</span>
                <span>•</span>
                <span>Storage: SQLite Local</span>
              </div>

              {/* Mono Code Block */}
              <div className="relative">
                <pre className="p-4 rounded-lg bg-bg-base border border-border-subtle font-mono text-xs text-text-primary overflow-y-auto max-h-[60vh] whitespace-pre-wrap leading-relaxed select-text">
                  {generatedPrompt}
                </pre>
              </div>
            </div>

            {/* Drawer Actions */}
            <div className="pt-4 border-t border-border-subtle flex justify-end space-x-3">
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="px-4 py-2 text-xs rounded-lg btn-secondary-ice font-medium"
              >
                Close
              </button>
              <button
                onClick={handleCopyFullContext}
                className="px-4 py-2 text-xs rounded-lg btn-magma font-semibold flex items-center space-x-1.5 shadow-md"
              >
                {isCopiedContext ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{isCopiedContext ? 'Copied' : 'Copy Full Context'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
