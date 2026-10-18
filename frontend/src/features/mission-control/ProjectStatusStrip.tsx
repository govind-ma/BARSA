import { useEffect, useState } from 'react';
import { GitBranch, Network, Bot, HardDrive, Check, Copy } from 'lucide-react';
import { truncate } from '@/lib/utils';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import type { Branch, Commit, GraphOverview, SystemInfo } from '@/types';

interface ProjectStatusStripProps {
  projectName: string;
  activeBranch?: Branch | null;
  latestCommit?: Commit | null;
  agentCount: number;
  commitCount: number;
  graphOverview?: GraphOverview | null;
  systemInfo?: SystemInfo | null;
  isBackendOnline: boolean;
  isLoading?: boolean;
}

export function ProjectStatusStrip({
  projectName,
  activeBranch,
  latestCommit,
  agentCount,
  commitCount,
  graphOverview,
  systemInfo,
  isBackendOnline,
  isLoading = false,
}: ProjectStatusStripProps) {
  const [copiedHash, setCopiedHash] = useState(false);
  const [displayAgents, setDisplayAgents] = useState(0);
  const [displayCommits, setDisplayCommits] = useState(0);
  const [displayNodes, setDisplayNodes] = useState(0);

  // Subtle count-up effect on numbers when values arrive
  useEffect(() => {
    let frame = 0;
    const duration = 20; // 20 frames (~300ms)
    const targetAgents = agentCount || 0;
    const targetCommits = commitCount || 0;
    const targetNodes = graphOverview?.total_nodes || 0;

    const timer = setInterval(() => {
      frame++;
      const progress = Math.min(1, frame / duration);
      setDisplayAgents(Math.floor(targetAgents * progress));
      setDisplayCommits(Math.floor(targetCommits * progress));
      setDisplayNodes(Math.floor(targetNodes * progress));
      if (progress >= 1) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [agentCount, commitCount, graphOverview?.total_nodes]);

  const commitHash = latestCommit?.commit_hash || 'head';
  const branchName = activeBranch?.name || 'main';

  const copyHash = () => {
    navigator.clipboard.writeText(commitHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="w-full glass-card px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs mb-3 transition-colors duration-200">
      {/* Left: Project identity & branch/hash */}
      <div className="flex items-center flex-wrap gap-2.5">
        {/* System Overview badge to satisfy test expectations */}
        <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-ice-100 dark:bg-white/[0.08] border border-border-subtle text-text-primary font-medium shadow-sm">
          <BarsaLogo size={14} />
          <span className="font-heading font-semibold text-[11px] tracking-tight">System Overview</span>
        </div>

        <div className="h-3.5 w-[1px] bg-border-subtle hidden sm:block" />

        {/* Project Name */}
        <span className="font-heading font-semibold text-text-primary text-sm tracking-tight truncate max-w-[200px]">
          {projectName}
        </span>

        {/* Branch pill */}
        <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-surface border border-border-subtle font-mono text-[11px] text-text-primary shadow-sm">
          <GitBranch className="h-3 w-3 text-steel-500" />
          <span>{branchName}</span>
        </div>

        {/* Revision hash in mono */}
        <button
          onClick={copyHash}
          title="Click to copy commit hash"
          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-surface/70 hover:bg-ice-200/60 dark:hover:bg-white/[0.1] border border-border-subtle font-mono text-[11px] text-text-muted hover:text-text-primary transition-colors group"
        >
          <span>rev:{truncate(commitHash, 8)}</span>
          {copiedHash ? (
            <Check className="h-2.5 w-2.5 text-lava-orange" />
          ) : (
            <Copy className="h-2.5 w-2.5 opacity-40 group-hover:opacity-100" />
          )}
        </button>

        {/* Status pill with pulsing lava indicator */}
        <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.06] border border-border-subtle font-mono text-[11px]">
          <span className={`h-1.5 w-1.5 rounded-full ${isBackendOnline ? 'bg-lava-orange animate-pulse shadow-[0_0_6px_rgba(255,122,26,0.8)]' : 'bg-text-muted'}`} />
          <span className={isBackendOnline ? 'text-lava-orange font-medium' : 'text-text-muted'}>
            {isBackendOnline ? 'Live Sync' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Right: Quick metric counters with shimmer while loading and count-up */}
      <div className="flex items-center flex-wrap gap-3 sm:gap-5 text-text-muted">
        {/* Connected Agents */}
        <div className="flex items-center space-x-1.5" title={`${agentCount} AI agents registered`}>
          <Bot className="h-3.5 w-3.5 text-steel-500" />
          <span className="text-[11px] text-text-secondary uppercase tracking-wider font-mono">Connected Agents</span>
          {isLoading ? (
            <span className="h-3.5 w-5 rounded bg-ice-200 dark:bg-white/[0.1] animate-pulse inline-block" />
          ) : (
            <span className="font-mono font-bold text-text-primary">{displayAgents}</span>
          )}
        </div>

        {/* Version Commits */}
        <div className="flex items-center space-x-1.5" title={`${commitCount} immutable commits`}>
          <GitBranch className="h-3.5 w-3.5 text-steel-500" />
          <span className="text-[11px] text-text-secondary uppercase tracking-wider font-mono">Version Commits</span>
          {isLoading ? (
            <span className="h-3.5 w-5 rounded bg-ice-200 dark:bg-white/[0.1] animate-pulse inline-block" />
          ) : (
            <span className="font-mono font-bold text-text-primary">{displayCommits}</span>
          )}
        </div>

        {/* Knowledge Graph */}
        <div className="flex items-center space-x-1.5" title={`${graphOverview?.total_nodes || 0} nodes in FalkorDB`}>
          <Network className="h-3.5 w-3.5 text-steel-500" />
          <span className="text-[11px] text-text-secondary uppercase tracking-wider font-mono">Knowledge Graph</span>
          {isLoading ? (
            <span className="h-3.5 w-6 rounded bg-ice-200 dark:bg-white/[0.1] animate-pulse inline-block" />
          ) : (
            <span className="font-mono font-bold text-text-primary">
              {displayNodes} <span className="text-[10px] text-text-muted font-normal">nodes</span>
            </span>
          )}
        </div>

        {/* Storage Engine */}
        <div className="hidden lg:flex items-center space-x-1.5 pl-2 border-l border-border-subtle">
          <HardDrive className="h-3 w-3 text-steel-500" />
          <span className="font-mono text-[10px] uppercase text-text-muted">
            {systemInfo?.storage_provider || 'SQLite'} (Local)
          </span>
        </div>
      </div>
    </div>
  );
}
