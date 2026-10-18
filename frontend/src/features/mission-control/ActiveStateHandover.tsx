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
  Sparkles,
  X,
} from 'lucide-react';
import { formatDate, truncate } from '@/lib/utils';
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
  const generatedPrompt =
    fullContextPrompt ||
    `[BARSA Universal AI Handover Protocol v0.1]
Project: ${projectName}
Active Task: ${activeTask?.task_id || 'TASK-NEXT'} (${activeTask?.title || 'Execution phase'})
Next Action: ${
      (lastCheckpoint?.attributes as any)?.next_action ||
      whyReadyText ||
      'Inspect verified FalkorDB dependencies and proceed with implementation'
    }
Latest Checkpoint: ${lastCheckpoint?.record_id || (lastCheckpoint as any)?.id || 'rec_cp_01'}
Base Commit: ${(lastCheckpoint?.attributes as any)?.base_revision || 'head'}
Instruction: Resume work without losing context. All prior ADRs and commits are locked in local BMS memory.`;

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
      <div className="flex flex-col h-full bg-card/60 backdrop-blur-md border border-ice/20 rounded-2xl p-4 shadow-[0_8px_32px_rgba(0,0,0,0.3)] select-none animate-page-enter">
        {/* Back Button */}
        <button
          onClick={onClearSelectedNode}
          className="inline-flex items-center space-x-1.5 text-xs text-ice hover:text-ice/80 font-medium mb-3 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Active Task</span>
        </button>

        {/* Node Detail Header */}
        <div className="pb-3 border-b border-ice/15 mb-3">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-ice/15 text-ice border border-ice/30 font-mono font-bold uppercase">
              {selectedNode.type || 'Entity'}
            </span>
            <span className="text-xs font-mono text-muted-foreground truncate">
              {selectedNode.id}
            </span>
          </div>
          <h3 className="text-base font-bold text-foreground tracking-tight">
            {selectedNode.label || selectedNode.id}
          </h3>
        </div>

        {/* Scrollable details */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4 text-xs">
          {/* Properties */}
          <div>
            <h4 className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold mb-1.5">
              Properties
            </h4>
            <div className="bg-secondary/40 rounded-xl p-2.5 border border-border/60 space-y-1 font-mono text-[11px]">
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 ? (
                Object.entries(selectedNode.properties).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-muted-foreground">{k}:</span>
                    <span className="text-foreground truncate">{String(v)}</span>
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground italic">No extra properties</div>
              )}
            </div>
          </div>

          {/* Relationships */}
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 rounded-xl bg-secondary/30 border border-border/50">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block mb-1">
                Inbound ({nodeRelationships?.inbound.length || 0})
              </span>
              <div className="space-y-1 font-mono text-[10px] text-ice">
                {nodeRelationships?.inbound.slice(0, 3).map((e, idx) => (
                  <div key={idx} className="truncate">
                    ← {e.type} ({truncate(e.source, 8)})
                  </div>
                ))}
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-secondary/30 border border-border/50">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block mb-1">
                Outbound ({nodeRelationships?.outbound.length || 0})
              </span>
              <div className="space-y-1 font-mono text-[10px] text-ice">
                {nodeRelationships?.outbound.slice(0, 3).map((e, idx) => (
                  <div key={idx} className="truncate">
                    → {e.type} ({truncate(e.target, 8)})
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Cypher Path */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold">
                FalkorDB Cypher Query
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(cypherSnippet);
                  onTriggerToast('Cypher query copied to clipboard.');
                }}
                className="text-[10px] text-ice hover:underline font-mono"
              >
                Copy
              </button>
            </div>
            <pre className="p-2.5 rounded-xl bg-[#090d14] border border-ice/20 font-mono text-[10px] text-ice overflow-x-auto leading-relaxed">
              {cypherSnippet}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // Normal View: Active State & Handover
  const nextActionText =
    (lastCheckpoint?.attributes as any)?.next_action ||
    whyReadyText ||
    'Verify all FalkorDB dependencies and initialize feature implementation.';

  return (
    <>
      <div className="flex flex-col h-full bg-card/60 backdrop-blur-md border border-ice/15 rounded-2xl p-4 shadow-[0_8px_32px_rgba(0,0,0,0.3)] select-none">
        {/* Pane Header */}
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-ice/10">
          <div className="flex items-center space-x-2">
            <div className="h-6 w-6 rounded-lg bg-ice/10 border border-ice/25 flex items-center justify-center text-ice">
              <Layers className="h-3.5 w-3.5" />
            </div>
            <div>
              <h3 className="text-xs font-bold tracking-tight text-foreground uppercase">
                Active State & Handover
              </h3>
              <span className="text-[10px] text-muted-foreground block -mt-0.5">
                Zero-cloud synchronization
              </span>
            </div>
          </div>

          <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono font-medium">
            Ready
          </span>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4">
          {/* Active Task Card */}
          <div className="p-3.5 rounded-xl bg-card/80 border border-ice/20 shadow-sm space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-ice px-2 py-0.5 rounded bg-ice/10 border border-ice/20">
                {activeTask?.task_id || 'TASK-RECOMMENDED'}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-semibold uppercase">
                {activeTask?.priority || 'High'}
              </span>
            </div>

            <h4 className="text-xs font-bold text-foreground leading-snug">
              {activeTask?.title || 'FalkorDB Multi-Agent Coordination Pipeline'}
            </h4>

            <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/50">
              <span>Dependencies: {activeTask?.dependencies?.length ?? 2} satisfied</span>
              {activeTask?.blockers && activeTask.blockers.length > 0 ? (
                <span className="text-chilli flex items-center space-x-1">
                  <AlertTriangle className="h-3 w-3" />
                  <span>{activeTask.blockers.length} Blocker</span>
                </span>
              ) : (
                <span className="text-emerald-400 font-mono">0 Blockers</span>
              )}
            </div>
          </div>

          {/* Next Action Callout (Large with ice left border) */}
          <div className="p-3.5 rounded-r-xl border-l-4 border-ice bg-ice/10 border-y border-r border-ice/20 shadow-[0_0_15px_rgba(56,189,248,0.1)] space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[10px] font-mono font-bold uppercase text-ice tracking-wider">
              <ArrowRight className="h-3 w-3 text-ice" />
              <span>Next Action Callout</span>
            </div>
            <p className="text-xs text-foreground font-semibold leading-relaxed">
              {nextActionText}
            </p>
          </div>

          {/* Last Checkpoint Card */}
          <div className="p-3 rounded-xl bg-secondary/30 border border-border/60 space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase font-bold text-muted-foreground flex items-center space-x-1">
                <BookmarkCheck className="h-3 w-3 text-ice" />
                <span>Last Checkpoint</span>
              </span>
              <span className="font-mono text-[10px] text-ice font-bold">
                {truncate(lastCheckpoint?.record_id || (lastCheckpoint as any)?.id || 'rec_cp_init', 12)}
              </span>
            </div>

            <div className="flex justify-between text-[11px] text-muted-foreground">
              <span className="flex items-center space-x-1">
                <Bot className="h-3 w-3 text-ice" />
                <span>{lastCheckpoint?.author || 'claude-architect'}</span>
              </span>
              <span className="flex items-center space-x-1">
                <Clock className="h-3 w-3" />
                <span>{formatDate(lastCheckpoint?.created_at || new Date().toISOString())}</span>
              </span>
            </div>

            <div className="flex items-center space-x-1 font-mono text-[10px] text-muted-foreground pt-1 border-t border-border/40">
              <GitCommit className="h-3 w-3" />
              <span>Base: {truncate((lastCheckpoint?.attributes as any)?.base_revision || 'head', 10)}</span>
            </div>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="pt-3 border-t border-ice/15 space-y-2 mt-2">
          {/* Primary Button: Copy handover prompt */}
          <button
            onClick={handleCopyHandoverPrompt}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-[0_0_20px_rgba(56,189,248,0.4)] transition-all active:scale-[0.98]"
            title="Copies full continuation prompt for ChatGPT, Claude, or Cursor"
          >
            {isCopiedPrompt ? (
              <>
                <Check className="h-4 w-4" />
                <span>Prompt Copied!</span>
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
            className="w-full flex items-center justify-center space-x-2 py-2 px-4 rounded-xl border border-ice/25 hover:border-ice/50 bg-secondary/40 hover:bg-secondary/70 text-foreground text-xs font-medium transition-all"
          >
            <FileCode className="h-3.5 w-3.5 text-ice" />
            <span>View full context</span>
          </button>
        </div>
      </div>

      {/* Right Drawer: Compressed Token-Optimized Prompt */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-page-enter">
          <div className="w-full max-w-lg h-full bg-card border-l border-ice/20 p-6 flex flex-col justify-between shadow-[0_0_50px_rgba(0,0,0,0.8)]">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-ice/15">
                <div className="flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-ice" />
                  <h3 className="text-sm font-bold text-foreground">
                    Compressed Smart Context Package
                  </h3>
                </div>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-center space-x-3 text-xs text-muted-foreground font-mono">
                <span>Tokens: ~420</span>
                <span>•</span>
                <span>Standard: BMS v0.1</span>
                <span>•</span>
                <span>Storage: SQLite Local</span>
              </div>

              {/* Mono Code Block */}
              <div className="relative">
                <pre className="p-4 rounded-xl bg-[#090d14] border border-ice/20 font-mono text-xs text-foreground/90 overflow-y-auto max-h-[60vh] whitespace-pre-wrap leading-relaxed select-text">
                  {generatedPrompt}
                </pre>
              </div>
            </div>

            {/* Drawer Actions */}
            <div className="pt-4 border-t border-border flex justify-end space-x-3">
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="px-4 py-2 text-xs rounded-xl border border-border hover:bg-secondary"
              >
                Close
              </button>
              <button
                onClick={handleCopyFullContext}
                className="px-4 py-2 text-xs rounded-xl bg-ice hover:bg-ice/90 text-background font-bold shadow-[0_0_15px_rgba(56,189,248,0.4)] flex items-center space-x-1.5"
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
