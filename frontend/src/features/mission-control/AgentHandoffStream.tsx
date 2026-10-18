import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Bot,
  User,
  FolderGit2,
} from 'lucide-react';
import { formatRelativeTime, truncate } from '@/lib/utils';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import { EmberSparks } from '@/components/ui/EmberSparks';
import type { Commit, BMSRecord } from '@/types';

export interface TimelineItem {
  id: string;
  type: 'commit' | 'checkpoint';
  author: string;
  isHuman: boolean;
  codeId: string;
  title: string;
  timestamp: string;
  rawCommit?: Commit;
  rawCheckpoint?: BMSRecord;
  completedActions?: string[];
  pendingActions?: string[];
  baseRevision?: string;
  isNew?: boolean;
}

interface AgentHandoffStreamProps {
  commits: Commit[];
  checkpoints: BMSRecord[];
  isLoading: boolean;
  onHoverItem?: (nodeId: string | null) => void;
  onSelectItem?: (nodeId: string) => void;
  onLoadSampleProject?: () => void;
}

export function AgentHandoffStream({
  commits,
  checkpoints,
  isLoading,
  onHoverItem,
  onSelectItem,
  onLoadSampleProject,
}: AgentHandoffStreamProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Combine and sort commits & checkpoints descending by timestamp
  const items: TimelineItem[] = React.useMemo(() => {
    const list: TimelineItem[] = [];

    commits.forEach((c) => {
      const authorName = c.author?.name || 'agent-ai';
      const isHuman = /human|user|alice|owner|developer/i.test(authorName);
      list.push({
        id: `commit-${c.commit_hash}`,
        type: 'commit',
        author: authorName,
        isHuman,
        codeId: c.commit_hash.slice(0, 7),
        title: c.message,
        timestamp: c.timestamp,
        rawCommit: c,
        baseRevision: c.parent_hashes?.[0],
      });
    });

    checkpoints.forEach((cp) => {
      const authorName = cp.author || (cp.attributes as any)?.created_by || 'claude-architect';
      const isHuman = /human|user|owner/i.test(authorName);
      const cpId = cp.record_id || (cp as any).id || 'cp';
      list.push({
        id: `checkpoint-${cpId}`,
        type: 'checkpoint',
        author: authorName,
        isHuman,
        codeId: cpId.length > 12 ? truncate(cpId, 10) : cpId,
        title: cp.title || cp.summary || 'Milestone Checkpoint',
        timestamp: cp.created_at,
        rawCheckpoint: cp,
        completedActions: (cp.attributes as any)?.completed_actions || [],
        pendingActions: (cp.attributes as any)?.pending_actions || [(cp.attributes as any)?.next_action].filter(Boolean),
        baseRevision: (cp.attributes as any)?.base_revision || (cp.attributes as any)?.commit_hash,
      });
    });

    list.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    return list;
  }, [commits, checkpoints]);

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const getAgentColorStyle = (author: string, isHuman: boolean) => {
    if (isHuman) {
      return {
        badge: 'bg-ice-100 text-steel-700 border-border-subtle',
        avatarBg: 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary',
      };
    }
    if (/claude|anthropic/i.test(author)) {
      return {
        badge: 'bg-ice-100 dark:bg-white/[0.08] text-text-primary border-border-subtle',
        avatarBg: 'bg-ice-200 dark:bg-white/[0.12] text-text-primary border border-border-subtle',
      };
    }
    if (/gpt|openai|chatgpt/i.test(author)) {
      return {
        badge: 'bg-ice-100 text-steel-700 border-border-subtle',
        avatarBg: 'bg-ice-200 text-steel-700 border border-border-subtle',
      };
    }
    return {
      badge: 'bg-lava-yellow/15 text-lava-orange border-lava-yellow/30 font-medium',
      avatarBg: 'bg-lava-yellow/20 text-lava-orange border border-lava-yellow/40',
    };
  };

  return (
    <div className="flex flex-col h-full glass-card p-3.5 shadow-md select-none relative overflow-hidden">
      {/* Pane Header */}
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-border-subtle">
        <div className="flex items-center space-x-2">
          <div className="h-6 w-6 rounded-md bg-ice-100 dark:bg-white/[0.08] border border-border-subtle flex items-center justify-center">
            <BarsaLogo size={14} />
          </div>
          <div>
            <h3 className="font-heading text-xs font-semibold tracking-tight text-text-primary uppercase">
              Agent Handoff Stream
            </h3>
            <span className="text-[10px] text-text-muted block -mt-0.5 font-mono">
              Multi-agent memory timeline
            </span>
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary border border-border-subtle font-mono">
          {items.length} items
        </span>
      </div>

      {/* Stream List */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 relative">
        {/* Continuous gradient spine */}
        {items.length > 1 && (
          <div className="absolute left-[15px] top-4 bottom-4 w-[2px] bg-gradient-to-b from-ice-300 via-ice-200 to-transparent dark:from-white/20 dark:via-white/10 pointer-events-none" />
        )}

        {isLoading ? (
          // Skeleton shimmer loader
          <div className="space-y-3 pt-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-16 rounded-lg bg-surface/60 border border-border-subtle animate-pulse flex items-center p-3 space-x-3"
              >
                <div className="h-7 w-7 rounded-full bg-ice-200 dark:bg-white/[0.1] shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 bg-ice-200 dark:bg-white/[0.1] rounded w-3/4" />
                  <div className="h-2.5 bg-ice-100 dark:bg-white/[0.06] rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          /* Empty Handoff Stream designed state with subtle ember particles */
          <div className="relative overflow-hidden py-10 px-4 text-center rounded-xl border border-dashed border-border-subtle bg-surface/40 my-auto">
            <EmberSparks count={4} />
            {/* Faint ghost timeline cards */}
            <div className="opacity-40 space-y-2 mb-3 max-w-[200px] mx-auto pointer-events-none">
              <div className="h-8 rounded bg-ice-200 dark:bg-white/[0.08] border border-border-subtle flex items-center px-2 space-x-2">
                <div className="h-3 w-3 rounded-full bg-steel-500" />
                <div className="h-2 bg-steel-500/50 rounded flex-1" />
              </div>
              <div className="h-8 rounded bg-ice-100 dark:bg-white/[0.05] border border-border-subtle flex items-center px-2 space-x-2">
                <div className="h-3 w-3 rounded-full bg-steel-500/60" />
                <div className="h-2 bg-steel-500/30 rounded flex-1" />
              </div>
            </div>

            <p className="font-heading font-medium text-xs text-text-primary">
              Your stream appears as agents work
            </p>
            <p className="text-[11px] text-text-muted mt-0.5">
              Commits, checkpoints, and handoffs will stream here in real-time.
            </p>
            {onLoadSampleProject && (
              <button
                onClick={onLoadSampleProject}
                className="mt-3.5 inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium shadow-sm"
              >
                <FolderGit2 className="h-3.5 w-3.5 text-steel-500" />
                <span>Load sample project</span>
              </button>
            )}
          </div>
        ) : (
          items.map((item, index) => {
            const nextItem = items[index + 1];
            const isHandoff =
              nextItem &&
              item.author.toLowerCase() !== nextItem.author.toLowerCase();
            const colors = getAgentColorStyle(item.author, item.isHuman);
            const isExpanded = expandedId === item.id;

            return (
              <div key={item.id} className="relative z-10 group">
                {/* Main Card */}
                <div
                  onClick={() => {
                    if (onSelectItem) {
                      onSelectItem(item.codeId);
                    }
                  }}
                  onMouseEnter={() => onHoverItem?.(item.codeId)}
                  onMouseLeave={() => onHoverItem?.(null)}
                  className={`relative p-2.5 rounded-lg border transition-all cursor-pointer ${
                    isExpanded
                      ? 'bg-surface border-border-strong shadow-md'
                      : 'bg-surface/80 hover:bg-surface border-border-subtle hover:border-border-strong hover:-translate-y-0.5 shadow-sm'
                  }`}
                >
                  <div className="flex items-start space-x-2.5">
                    {/* Agent Avatar */}
                    <div
                      className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-xs font-mono font-bold shadow-sm ${colors.avatarBg}`}
                      title={`Agent: ${item.author}`}
                    >
                      {item.isHuman ? (
                        <User className="h-3.5 w-3.5" />
                      ) : (
                        <Bot className="h-3.5 w-3.5" />
                      )}
                    </div>

                    {/* Content preview */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-semibold text-text-primary truncate">
                          {item.author}
                        </span>
                        <span className="text-[10px] text-text-muted font-mono shrink-0">
                          {formatRelativeTime(item.timestamp)}
                        </span>
                      </div>

                      {/* Pill & ID */}
                      <div className="flex items-center space-x-1.5 mt-0.5">
                        <span
                          className={`text-[9px] uppercase font-mono px-1.5 py-0.2 rounded border font-medium ${
                            item.type === 'checkpoint'
                              ? 'bg-lava-yellow/15 text-lava-orange dark:text-lava-yellow border-lava-yellow/30'
                              : 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary border-border-subtle'
                          }`}
                        >
                          {item.type}
                        </span>
                        <span className="font-mono text-[10px] text-text-muted">
                          {item.codeId}
                        </span>
                        <p className="text-[11px] text-text-secondary truncate leading-snug">
                          {item.title}
                        </p>
                      </div>
                    </div>

                    {/* Expand/Collapse Chevron */}
                    <button
                      onClick={(e) => toggleExpand(item.id, e)}
                      aria-label="Toggle details"
                      className="p-0.5 rounded text-text-muted hover:text-text-primary transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-lava-orange" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 opacity-60 group-hover:opacity-100" />
                      )}
                    </button>
                  </div>

                  {/* Inline Expanded Details */}
                  {isExpanded && (
                    <div className="mt-2.5 pt-2 border-t border-border-subtle text-[11px] space-y-1.5 animate-page-enter">
                      <div className="flex justify-between text-text-muted">
                        <span>Full Author:</span>
                        <span className="text-text-primary font-mono">{item.author}</span>
                      </div>

                      {item.baseRevision && (
                        <div className="flex justify-between text-text-muted">
                          <span>Base Commit:</span>
                          <span className="font-mono text-steel-700 dark:text-text-secondary">
                            {truncate(item.baseRevision, 12)}
                          </span>
                        </div>
                      )}

                      {item.completedActions && item.completedActions.length > 0 && (
                        <div className="space-y-0.5 pt-1">
                          <span className="text-[10px] uppercase font-mono font-bold text-steel-700 dark:text-text-secondary tracking-wider">
                            Completed Actions:
                          </span>
                          <ul className="pl-3 space-y-0.5 list-disc marker:text-steel-500 text-text-secondary text-[10px]">
                            {item.completedActions.map((act, aIdx) => (
                              <li key={aIdx}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {item.pendingActions && item.pendingActions.length > 0 && (
                        <div className="space-y-0.5 pt-1">
                          <span className="text-[10px] uppercase font-mono font-bold text-lava-orange tracking-wider">
                            Pending / Next:
                          </span>
                          <ul className="pl-3 space-y-0.5 list-disc marker:text-lava-orange text-text-primary text-[10px]">
                            {item.pendingActions.map((act, aIdx) => (
                              <li key={aIdx}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Handoff Connector Row if author transitioned */}
                {isHandoff && (
                  <div className="my-1.5 flex items-center justify-center">
                    <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] border border-border-subtle text-text-primary text-[9px] font-mono shadow-sm">
                      <span className="truncate max-w-[70px]">{truncate(nextItem.author, 10)}</span>
                      <ArrowRight className="h-2.5 w-2.5 text-lava-orange animate-pulse" />
                      <span className="truncate max-w-[70px] font-bold">{truncate(item.author, 10)}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
