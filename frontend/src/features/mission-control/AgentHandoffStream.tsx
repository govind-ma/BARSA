import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Bot,
  User,
  Clock,
  Sparkles,
} from 'lucide-react';
import { formatRelativeTime, truncate } from '@/lib/utils';
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
}

export function AgentHandoffStream({
  commits,
  checkpoints,
  isLoading,
  onHoverItem,
  onSelectItem,
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
        badge: 'bg-secondary/70 text-muted-foreground border-border/80',
        avatarBg: 'bg-secondary text-muted-foreground',
      };
    }
    if (/claude|anthropic/i.test(author)) {
      return {
        badge: 'bg-ice/15 text-ice border-ice/30 shadow-[0_0_8px_rgba(56,189,248,0.25)]',
        avatarBg: 'bg-ice/20 text-ice border border-ice/40',
      };
    }
    if (/gpt|openai|chatgpt/i.test(author)) {
      return {
        badge: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
        avatarBg: 'bg-teal-500/20 text-teal-300 border border-teal-500/40',
      };
    }
    return {
      badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
      avatarBg: 'bg-amber-500/20 text-amber-300 border border-amber-500/40',
    };
  };

  return (
    <div className="flex flex-col h-full bg-card/60 backdrop-blur-md border border-ice/15 rounded-2xl p-3.5 shadow-[0_8px_32px_rgba(0,0,0,0.3)] select-none">
      {/* Pane Header */}
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-ice/10">
        <div className="flex items-center space-x-2">
          <div className="h-6 w-6 rounded-lg bg-ice/10 border border-ice/25 flex items-center justify-center text-ice">
            <Sparkles className="h-3 w-3" />
          </div>
          <div>
            <h3 className="text-xs font-bold tracking-tight text-foreground uppercase">
              Agent Handoff Stream
            </h3>
            <span className="text-[10px] text-muted-foreground block -mt-0.5">
              Multi-agent memory timeline
            </span>
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-ice/10 text-ice border border-ice/20 font-mono">
          {items.length} items
        </span>
      </div>

      {/* Stream List */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 relative">
        {/* Continuous gradient spine */}
        {items.length > 1 && (
          <div className="absolute left-[15px] top-4 bottom-4 w-[2px] bg-gradient-to-b from-ice/50 via-ice/25 to-transparent pointer-events-none" />
        )}

        {isLoading ? (
          // Skeleton shimmer loader
          <div className="space-y-3 pt-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-16 rounded-xl bg-secondary/30 border border-border/40 animate-pulse flex items-center p-3 space-x-3"
              >
                <div className="h-7 w-7 rounded-full bg-secondary/60 shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 bg-secondary/70 rounded w-3/4" />
                  <div className="h-2.5 bg-secondary/50 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-xs text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 text-muted-foreground/60" />
            <p className="font-medium text-foreground">No handoffs yet</p>
            <p className="text-[11px] mt-1 text-muted-foreground">
              Commits and checkpoints will stream here as AI agents operate.
            </p>
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
                  className={`relative p-2.5 rounded-xl border transition-all cursor-pointer ${
                    isExpanded
                      ? 'bg-card/90 border-ice/40 shadow-[0_0_15px_rgba(56,189,248,0.15)]'
                      : 'bg-card/45 hover:bg-card/75 border-border/60 hover:border-ice/30'
                  }`}
                >
                  <div className="flex items-start space-x-2.5">
                    {/* Agent Avatar */}
                    <div
                      className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold font-mono ${colors.avatarBg}`}
                      title={`Author: ${item.author}`}
                    >
                      {item.isHuman ? (
                        <User className="h-3.5 w-3.5" />
                      ) : (
                        <Bot className="h-3.5 w-3.5" />
                      )}
                    </div>

                    {/* Metadata & Title */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="text-[11px] font-semibold text-foreground truncate max-w-[110px]">
                          {item.author}
                        </span>

                        <div className="flex items-center space-x-1 shrink-0">
                          {/* Type Pill */}
                          <span
                            className={`text-[9px] px-1.5 py-0.2 rounded-full border font-mono font-medium ${
                              item.type === 'checkpoint'
                                ? 'bg-ice/15 text-ice border-ice/30'
                                : 'bg-secondary/70 text-muted-foreground border-border/60'
                            }`}
                          >
                            {item.type === 'checkpoint' ? 'Checkpoint' : 'Commit'}
                          </span>

                          <span className="text-[10px] text-muted-foreground font-mono">
                            {formatRelativeTime(item.timestamp)}
                          </span>
                        </div>
                      </div>

                      {/* Hash or CP ID + Message */}
                      <div className="flex items-baseline space-x-1.5">
                        <span className="font-mono text-[10px] text-ice font-bold shrink-0">
                          {item.codeId}
                        </span>
                        <p className="text-[11px] text-foreground/90 truncate leading-snug">
                          {item.title}
                        </p>
                      </div>
                    </div>

                    {/* Expand/Collapse Chevron */}
                    <button
                      onClick={(e) => toggleExpand(item.id, e)}
                      aria-label="Toggle details"
                      className="p-0.5 rounded text-muted-foreground hover:text-ice transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-ice" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 opacity-60 group-hover:opacity-100" />
                      )}
                    </button>
                  </div>

                  {/* Inline Expanded Details */}
                  {isExpanded && (
                    <div className="mt-2.5 pt-2 border-t border-border/60 text-[11px] space-y-1.5 animate-page-enter">
                      <div className="flex justify-between text-muted-foreground">
                        <span>Full Author:</span>
                        <span className="text-foreground font-mono">{item.author}</span>
                      </div>

                      {item.baseRevision && (
                        <div className="flex justify-between text-muted-foreground">
                          <span>Base Commit:</span>
                          <span className="font-mono text-ice">{truncate(item.baseRevision, 12)}</span>
                        </div>
                      )}

                      {item.completedActions && item.completedActions.length > 0 && (
                        <div className="space-y-0.5 pt-1">
                          <span className="text-[10px] uppercase font-mono font-bold text-ice tracking-wider">
                            Completed Actions:
                          </span>
                          <ul className="pl-3 space-y-0.5 list-disc marker:text-ice text-muted-foreground text-[10px]">
                            {item.completedActions.map((act, aIdx) => (
                              <li key={aIdx}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {item.pendingActions && item.pendingActions.length > 0 && (
                        <div className="space-y-0.5 pt-1">
                          <span className="text-[10px] uppercase font-mono font-bold text-amber-400 tracking-wider">
                            Pending / Next:
                          </span>
                          <ul className="pl-3 space-y-0.5 list-disc marker:text-amber-400 text-foreground text-[10px]">
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
                    <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-ice/10 border border-ice/25 text-ice text-[9px] font-mono shadow-[0_0_8px_rgba(56,189,248,0.2)]">
                      <span className="truncate max-w-[70px]">{truncate(nextItem.author, 10)}</span>
                      <ArrowRight className="h-2.5 w-2.5 text-chilli animate-pulse" />
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
