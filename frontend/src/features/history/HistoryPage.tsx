import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import { formatDate } from '@/lib/utils';
import type { Commit, BMSRecord } from '@/types';
import {
  History,
  GitBranch,
  GitCommit,
  BrainCircuit,
  BookmarkCheck,
  Bot,
  User,
  ArrowRight,
  Search,
} from 'lucide-react';

export interface TimelineEvent {
  id: string;
  type: 'commit' | 'decision' | 'checkpoint' | 'record';
  title: string;
  summary?: string;
  author: {
    name: string;
    isAgent: boolean;
    role?: string;
  };
  timestamp: string;
  metadata?: Record<string, any>;
  link?: string;
}

export function HistoryPage() {
  const { activeProject } = useApp();
  const [commits, setCommits] = useState<Commit[]>([]);
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [checkpoints, setCheckpoints] = useState<BMSRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filterType, setFilterType] = useState<'all' | 'commit' | 'decision' | 'checkpoint'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const loadHistoryData = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [cmtsRes, recsRes, chksRes] = await Promise.allSettled([
        api.listCommits(activeProject.project_id),
        api.listRecords(activeProject.project_id),
        api.listRecords(activeProject.project_id, 'checkpoint'),
      ]);
      if (cmtsRes.status === 'fulfilled') setCommits(cmtsRes.value);
      if (recsRes.status === 'fulfilled') setRecords(recsRes.value);
      if (chksRes.status === 'fulfilled') setCheckpoints(chksRes.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHistoryData();
  }, [activeProject?.project_id]);

  // Combine and sort events chronologically
  const timelineEvents: TimelineEvent[] = useMemo(() => {
    const list: TimelineEvent[] = [];

    // 1. Commits
    commits.forEach((c) => {
      const isAgent = !/human|owner|developer|user|alice/i.test(c.author?.name || '');
      list.push({
        id: `commit-${c.commit_hash}`,
        type: 'commit',
        title: c.message || 'Memory state commit',
        summary: `Saved revision on main branch`,
        author: {
          name: c.author?.name || 'AI Agent',
          isAgent,
          role: isAgent ? 'Agent' : 'Human',
        },
        timestamp: c.timestamp,
        metadata: { hash: c.commit_hash.substring(0, 7) },
        link: `/version-control`,
      });
    });

    // 2. Decisions & Records
    records.forEach((r) => {
      if (r.record_type === 'checkpoint') return; // Handled below
      const isDecision = r.record_type === 'decision';
      const isAgent = !/human|owner|developer|user/i.test(r.author || '');
      list.push({
        id: `rec-${r.record_id}`,
        type: isDecision ? 'decision' : 'record',
        title: r.title,
        summary: r.summary || (isDecision ? 'Architectural Decision Record' : 'Knowledge Record'),
        author: {
          name: r.author || 'AI Agent',
          isAgent,
          role: isAgent ? 'Agent' : 'Human',
        },
        timestamp: r.created_at,
        metadata: { status: r.verification_status, recordType: r.record_type },
        link: `/memory`,
      });
    });

    // 3. Checkpoints
    checkpoints.forEach((ck) => {
      list.push({
        id: `chk-${ck.record_id}`,
        type: 'checkpoint',
        title: ck.title || `Milestone Checkpoint: ${ck.record_id.substring(0, 8)}`,
        summary: ck.summary || 'Verified agent context & memory snapshot',
        author: {
          name: ck.author || 'System Agent',
          isAgent: true,
          role: 'Agent Snapshot',
        },
        timestamp: ck.created_at,
        metadata: { recordType: ck.record_type },
        link: `/checkpoints`,
      });
    });

    // Sort newest first
    return list.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [commits, records, checkpoints]);

  const filteredEvents = useMemo(() => {
    return timelineEvents.filter((ev) => {
      if (filterType !== 'all' && ev.type !== filterType) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          ev.title.toLowerCase().includes(q) ||
          ev.summary?.toLowerCase().includes(q) ||
          ev.author.name.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [timelineEvents, filterType, searchQuery]);

  if (!activeProject) {
    return (
      <EmptyState
        icon={<History className="h-10 w-10 text-text-muted" />}
        title="No Project Selected"
        description="Select or create a project to view its historical evolution and agent activity."
      />
    );
  }

  return (
    <div className="space-y-6 animate-page-enter">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Project History</h1>
          <p className="text-sm text-text-muted mt-0.5">
            A clear timeline of decisions, checkpoints, and memory commits made across your project.
          </p>
        </div>
        <div className="flex items-center space-x-2.5">
          <Link to="/version-control">
            <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs font-medium">
              <GitBranch className="h-3.5 w-3.5 mr-1.5 text-steel-500" />
              View Version History (DAG)
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Type Filter Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto p-1 rounded-xl solid-floating-surface">
          {(
            [
              { id: 'all', label: 'All Activity' },
              { id: 'decision', label: 'Decisions' },
              { id: 'checkpoint', label: 'Checkpoints' },
              { id: 'commit', label: 'Commits' },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filterType === tab.id
                  ? 'bg-ice-200 dark:bg-bg-elevated text-text-primary shadow-xs font-semibold'
                  : 'text-text-muted hover:text-text-primary hover:bg-ice-100/50 dark:hover:bg-white/[0.04]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search history..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl solid-floating-surface text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-steel-500"
          />
        </div>
      </div>

      {/* Timeline Stream */}
      {isLoading ? (
        <LoadingSpinner text="Retrieving project timeline..." />
      ) : filteredEvents.length === 0 ? (
        <EmptyState
          icon={<History className="h-10 w-10 text-text-muted" />}
          title="No Activity Found"
          description={
            searchQuery
              ? 'No historical events match your search query.'
              : 'As your agents record decisions, complete tasks, and create checkpoints, their activity will appear here in chronological order.'
          }
          actionLabel={searchQuery ? 'Clear search' : undefined}
          onAction={searchQuery ? () => setSearchQuery('') : undefined}
        />
      ) : (
        <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-border-subtle">
          {filteredEvents.map((ev) => {
            const isDecision = ev.type === 'decision';
            const isCheckpoint = ev.type === 'checkpoint';

            return (
              <div key={ev.id} className="relative group">
                {/* Timeline Dot Icon */}
                <div
                  className={`absolute -left-6 sm:-left-8 top-1.5 h-6 w-6 rounded-full border flex items-center justify-center transition-transform group-hover:scale-110 shadow-xs ${
                    isDecision
                      ? 'bg-amber-500/10 border-amber-500/40 text-amber-500'
                      : isCheckpoint
                      ? 'bg-lava-orange/10 border-lava-orange/40 text-lava-orange'
                      : 'bg-steel-500/10 border-steel-500/40 text-steel-500'
                  }`}
                >
                  {isDecision ? (
                    <BrainCircuit className="h-3 w-3" />
                  ) : isCheckpoint ? (
                    <BookmarkCheck className="h-3 w-3" />
                  ) : (
                    <GitCommit className="h-3 w-3" />
                  )}
                </div>

                {/* Event Card */}
                <div className="glass-card p-4 rounded-xl space-y-2 hover:border-border-strong transition-all">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm text-text-primary">
                        {ev.title}
                      </span>
                      {ev.metadata?.hash && (
                        <span className="px-1.5 py-0.5 rounded font-mono text-[10px] bg-ice-100 dark:bg-white/[0.06] text-text-muted">
                          {ev.metadata.hash}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-text-muted font-mono shrink-0">
                      {formatDate(ev.timestamp)}
                    </span>
                  </div>

                  {ev.summary && (
                    <p className="text-xs text-text-secondary leading-relaxed">
                      {ev.summary}
                    </p>
                  )}

                  {/* Author & Context Footer */}
                  <div className="flex items-center justify-between pt-2 border-t border-border-subtle text-xs">
                    <div className="flex items-center space-x-2">
                      <div className="flex items-center space-x-1.5 text-text-muted text-[11px]">
                        {ev.author.isAgent ? (
                          <Bot className="h-3.5 w-3.5 text-lava-orange" />
                        ) : (
                          <User className="h-3.5 w-3.5 text-steel-500" />
                        )}
                        <span className="font-medium text-text-secondary">
                          {ev.author.name}
                        </span>
                        {ev.author.role && (
                          <span className="text-[10px] text-text-muted font-mono">
                            ({ev.author.role})
                          </span>
                        )}
                      </div>
                    </div>

                    {ev.link && (
                      <Link
                        to={ev.link}
                        className="inline-flex items-center text-[11px] font-medium text-lava-orange hover:underline"
                      >
                        <span>Details</span>
                        <ArrowRight className="h-3 w-3 ml-1" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
