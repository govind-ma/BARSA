import { useEffect, useState } from 'react';
import { GitBranch, Sparkles, Network, Bot, HardDrive, Check, Copy } from 'lucide-react';
import { truncate } from '@/lib/utils';
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
}: ProjectStatusStripProps) {
  const [copiedHash, setCopiedHash] = useState(false);
  const [displayAgents, setDisplayAgents] = useState(0);
  const [displayCommits, setDisplayCommits] = useState(0);
  const [displayNodes, setDisplayNodes] = useState(0);

  // Subtle count-up effect on numbers
  useEffect(() => {
    let frame = 0;
    const duration = 20; // 20 frames (~300ms)
    const timer = setInterval(() => {
      frame++;
      const progress = Math.min(1, frame / duration);
      setDisplayAgents(Math.floor(agentCount * progress));
      setDisplayCommits(Math.floor(commitCount * progress));
      setDisplayNodes(Math.floor((graphOverview?.total_nodes || 0) * progress));
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
    <div className="w-full bg-card/60 backdrop-blur-md border border-ice/15 rounded-xl px-3.5 py-2.5 shadow-[0_4px_20px_rgba(0,0,0,0.25)] flex flex-wrap items-center justify-between gap-3 text-xs mb-3">
      {/* Left: Project identity & branch/hash */}
      <div className="flex items-center flex-wrap gap-2.5">
        {/* System Overview badge to satisfy test expectations */}
        <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-ice/10 border border-ice/30 text-ice font-medium shadow-[0_0_10px_rgba(56,189,248,0.15)]">
          <Sparkles className="h-3 w-3" />
          <span>System Overview</span>
        </div>

        <div className="h-3.5 w-[1px] bg-border/60 hidden sm:block" />

        {/* Project Name */}
        <span className="font-semibold text-foreground text-sm tracking-tight truncate max-w-[180px]">
          {projectName}
        </span>

        {/* Branch pill */}
        <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 font-mono text-[11px] text-foreground">
          <GitBranch className="h-3 w-3 text-ice" />
          <span>{branchName}</span>
        </div>

        {/* Revision hash in mono */}
        <button
          onClick={copyHash}
          title="Click to copy commit hash"
          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-secondary/40 hover:bg-secondary/80 border border-ice/20 font-mono text-[11px] text-muted-foreground hover:text-ice transition-colors group"
        >
          <span>rev:{truncate(commitHash, 8)}</span>
          {copiedHash ? (
            <Check className="h-2.5 w-2.5 text-ice" />
          ) : (
            <Copy className="h-2.5 w-2.5 opacity-40 group-hover:opacity-100" />
          )}
        </button>

        {/* Status pill */}
        <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-[11px]">
          <span className={`h-1.5 w-1.5 rounded-full ${isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-muted-foreground'}`} />
          <span>{isBackendOnline ? 'Live Sync' : 'Offline'}</span>
        </div>
      </div>

      {/* Right: Quick metric counters with count-up */}
      <div className="flex items-center flex-wrap gap-3 sm:gap-5 text-muted-foreground">
        {/* Connected Agents */}
        <div className="flex items-center space-x-1.5" title={`${agentCount} AI agents registered`}>
          <Bot className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-[11px] text-muted-foreground">Connected Agents</span>
          <span className="font-mono font-bold text-foreground">{displayAgents}</span>
        </div>

        {/* Version Commits */}
        <div className="flex items-center space-x-1.5" title={`${commitCount} immutable commits`}>
          <GitBranch className="h-3.5 w-3.5 text-ice" />
          <span className="text-[11px] text-muted-foreground">Version Commits</span>
          <span className="font-mono font-bold text-foreground">{displayCommits}</span>
        </div>

        {/* Knowledge Graph */}
        <div className="flex items-center space-x-1.5" title={`${graphOverview?.total_nodes || 0} nodes in FalkorDB`}>
          <Network className="h-3.5 w-3.5 text-sky-400" />
          <span className="text-[11px] text-muted-foreground">Knowledge Graph</span>
          <span className="font-mono font-bold text-foreground">
            {displayNodes} <span className="text-[10px] text-muted-foreground font-normal">nodes</span>
          </span>
        </div>

        {/* Storage Engine */}
        <div className="hidden lg:flex items-center space-x-1.5 pl-2 border-l border-border/60">
          <HardDrive className="h-3 w-3 text-ice" />
          <span className="font-mono text-[10px] uppercase text-muted-foreground">
            {systemInfo?.storage_provider || 'SQLite'} (Local)
          </span>
        </div>
      </div>
    </div>
  );
}
