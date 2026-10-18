import React, { useState, useMemo, useEffect } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  AlertTriangle,
  Play,
  ShieldAlert,
  FolderGit2,
} from 'lucide-react';
import { EmberSparks } from '@/components/ui/EmberSparks';
import type { GraphNode, GraphEdge } from '@/types';

interface LiveKnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  recommendedTaskId?: string | null;
  readinessScore?: number | null;
  whyReadyText?: string;
  selectedNodeId?: string | null;
  highlightedNodeId?: string | null;
  onSelectNode: (node: GraphNode | null) => void;
  onRunRerank: () => Promise<void>;
  onInjectBlocker: () => void;
  onLoadSampleProject?: () => void;
  isLoading?: boolean;
}

const FILTER_PILLS = [
  { id: 'ALL', label: 'All' },
  { id: 'TASK', label: 'Tasks' },
  { id: 'DECISION', label: 'Decisions' },
  { id: 'AGENT', label: 'Agents' },
  { id: 'CAPABILITY', label: 'Capabilities' },
  { id: 'ISSUE', label: 'Issues' },
];

export function LiveKnowledgeGraph({
  nodes,
  edges,
  recommendedTaskId,
  readinessScore,
  whyReadyText,
  selectedNodeId,
  highlightedNodeId,
  onSelectNode,
  onRunRerank,
  onInjectBlocker,
  onLoadSampleProject,
}: LiveKnowledgeGraphProps) {
  // Pan and Zoom
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Floating filter chips - default is "ALL" with "All" label
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

  // Hovered node for neighbor brightening
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Blocker popover state
  const [isBlockerPopoverOpen, setIsBlockerPopoverOpen] = useState(false);
  const [isReranking, setIsReranking] = useState(false);
  const [justReranked, setJustReranked] = useState(false);

  // Typewriter reasoning text
  const [displayedReasoning, setDisplayedReasoning] = useState('');
  const fullReasoning =
    whyReadyText ||
    (recommendedTaskId
      ? `All dependencies satisfied for ${recommendedTaskId}. 0 active blockers. Readiness ${readinessScore ?? '270.0'}.`
      : 'FalkorDB graph engine: Cypher multi-hop query analysis ready.');

  useEffect(() => {
    let index = 0;
    setDisplayedReasoning('');
    const timer = setInterval(() => {
      index++;
      setDisplayedReasoning(fullReasoning.slice(0, index));
      if (index >= fullReasoning.length) clearInterval(timer);
    }, 15);
    return () => clearInterval(timer);
  }, [fullReasoning]);

  // Compute 2D force/circular layout positions
  const nodePositions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    if (!nodes || nodes.length === 0) return map;

    const centerX = 360;
    const centerY = 240;
    const count = nodes.length;
    const radius = Math.min(220, 80 + count * 14);

    nodes.forEach((node, i) => {
      if (recommendedTaskId && node.id === recommendedTaskId) {
        map.set(node.id, { x: centerX - 30, y: centerY });
        return;
      }
      const angle = (2 * Math.PI * i) / count;
      map.set(node.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });

    return map;
  }, [nodes, recommendedTaskId]);

  // Neighbor map for hover brightening (neighbors stay bright, others dim to 25%)
  const neighborSet = useMemo(() => {
    const targetId = hoveredNodeId || highlightedNodeId;
    if (!targetId) return null;
    const set = new Set<string>([targetId]);
    edges.forEach((e) => {
      if (e.source === targetId) set.add(e.target);
      if (e.target === targetId) set.add(e.source);
    });
    return set;
  }, [hoveredNodeId, highlightedNodeId, edges]);

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'BUTTON') return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleResetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleRerankClick = async () => {
    setIsReranking(true);
    try {
      await onRunRerank();
      setJustReranked(true);
      setTimeout(() => setJustReranked(false), 2000);
    } finally {
      setIsReranking(false);
    }
  };

  const handleConfirmInjectBlocker = () => {
    setIsBlockerPopoverOpen(false);
    onInjectBlocker();
  };

  // Node Shape Renderer matching DESIGN_SYSTEM.md:
  // - Task = steel-500 circle with white inner ring
  // - Decision = lava-yellow hexagon
  // - Capability = ice-300 rounded square with steel border
  // - Agent = lava-orange diamond
  // - Issue = lava-red circle with soft red pulse
  // - Recommended node = magma gradient with pulsing glow ring and readiness badge
  const renderNodeShape = (node: GraphNode, pos: { x: number; y: number }, isRecommended: boolean) => {
    const type = (node.type || 'Task').toUpperCase();
    const isHovered = hoveredNodeId === node.id || highlightedNodeId === node.id;
    const isSelected = selectedNodeId === node.id;

    if (isRecommended) {
      return (
        <g>
          <circle
            cx={pos.x}
            cy={pos.y}
            r={24}
            fill="url(#magmaNodeGrad)"
            stroke="#FFFFFF"
            strokeWidth={2.5}
            className={`transition-all duration-300 ${justReranked ? 'filter drop-shadow-[0_0_24px_rgba(255,122,26,0.9)] scale-110' : 'filter drop-shadow-[0_0_15px_rgba(255,122,26,0.5)]'}`}
          />
          <circle cx={pos.x} cy={pos.y} r={16} fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth={1.5} />
        </g>
      );
    }

    if (type.includes('DECISION')) {
      // Hexagon in lava-yellow (#FFC93C)
      const r = 20;
      const points = [
        `${pos.x},${pos.y - r}`,
        `${pos.x + r * 0.86},${pos.y - r * 0.5}`,
        `${pos.x + r * 0.86},${pos.y + r * 0.5}`,
        `${pos.x},${pos.y + r}`,
        `${pos.x - r * 0.86},${pos.y + r * 0.5}`,
        `${pos.x - r * 0.86},${pos.y - r * 0.5}`,
      ].join(' ');

      return (
        <polygon
          points={points}
          fill="#FFC93C"
          stroke={isSelected ? '#0C0A0B' : isHovered ? '#FFFFFF' : '#FF7A1A'}
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(255,201,60,0.35)]"
        />
      );
    }

    if (type.includes('CAPABILITY')) {
      // Rounded square in ice-300 (#B3CDE0) with steel border
      const size = 32;
      return (
        <rect
          x={pos.x - size / 2}
          y={pos.y - size / 2}
          width={size}
          height={size}
          rx={6}
          fill="#B3CDE0"
          stroke={isSelected ? '#0D1A24' : '#6F8FA8'}
          strokeWidth={isSelected ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_6px_rgba(179,205,224,0.4)]"
        />
      );
    }

    if (type.includes('AGENT')) {
      // Diamond in lava-orange (#FF7A1A)
      const d = 19;
      const points = `${pos.x},${pos.y - d} ${pos.x + d},${pos.y} ${pos.x},${pos.y + d} ${pos.x - d},${pos.y}`;
      return (
        <polygon
          points={points}
          fill="#FF7A1A"
          stroke={isSelected ? '#FFFFFF' : '#E5301F'}
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_10px_rgba(255,122,26,0.4)]"
        />
      );
    }

    if (type.includes('ISSUE') || type.includes('BLOCKER')) {
      // Circle in lava-red (#E5301F) with soft pulse
      return (
        <g>
          <circle
            cx={pos.x}
            cy={pos.y}
            r={18}
            fill="#E5301F"
            stroke={isSelected ? '#FFFFFF' : '#A81414'}
            strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
            className="transition-all duration-200 filter drop-shadow-[0_0_12px_rgba(229,48,31,0.5)]"
          />
          <circle cx={pos.x} cy={pos.y} r={24} fill="none" stroke="#E5301F" strokeWidth={1} className="animate-ping opacity-30" />
        </g>
      );
    }

    // Default: Task (steel-500 circle with white inner ring)
    return (
      <g>
        <circle
          cx={pos.x}
          cy={pos.y}
          r={18}
          fill="#6F8FA8"
          stroke={isSelected ? '#FF7A1A' : isHovered ? '#3E5A72' : '#3E5A72'}
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(111,143,168,0.3)]"
        />
        <circle cx={pos.x} cy={pos.y} r={10} fill="none" stroke="#FFFFFF" strokeWidth={1.5} opacity={0.9} />
      </g>
    );
  };

  const hasNodes = nodes && nodes.length > 0;

  return (
    <div className="relative flex flex-col h-full glass-card overflow-hidden shadow-md select-none">
      {/* Lava line sweep during FalkorDB Re-rank */}
      {isReranking && (
        <div className="absolute top-0 left-0 right-0 h-1 z-30 overflow-hidden bg-ice-100">
          <div className="h-full w-1/3 bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red animate-lavaSweep shadow-[0_0_12px_rgba(255,122,26,0.8)]" />
        </div>
      )}

      {/* Top Floating Entity Filter Chips */}
      <div className="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-lg bg-surface/90 backdrop-blur-md border border-border-subtle shadow-sm pointer-events-auto">
          {FILTER_PILLS.map((chip) => {
            const isActive = activeFilter === chip.id;
            return (
              <button
                key={chip.id}
                onClick={() => setActiveFilter(chip.id)}
                className={`relative text-[11px] font-mono px-2.5 py-1 rounded-md transition-all duration-150 ${
                  isActive
                    ? 'bg-surface text-text-primary font-semibold shadow-sm border border-border-subtle'
                    : 'bg-ice-100 dark:bg-white/[0.04] text-steel-700 dark:text-text-secondary hover:text-text-primary hover:bg-ice-200'
                }`}
              >
                {chip.label}
                {isActive && (
                  <span className="absolute bottom-0 left-1 right-1 h-0.5 rounded-full bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red" />
                )}
              </button>
            );
          })}
        </div>

        {/* Dash Legend Pill per DESIGN_SYSTEM.md */}
        <div className="hidden sm:flex items-center space-x-3 px-3 py-1 rounded-lg bg-surface/90 backdrop-blur-md border border-border-subtle text-[10px] text-text-muted font-mono pointer-events-auto shadow-sm">
          <span className="flex items-center space-x-1" title="Solid steel edge">
            <span className="w-3 border-b-2 border-steel-500 inline-block opacity-70" />
            <span className="text-text-secondary">DEPENDS_ON</span>
          </span>
          <span className="flex items-center space-x-1" title="Dashed lava-red edge">
            <span className="w-3 border-b-2 border-dashed border-lava-red inline-block" />
            <span className="text-lava-red">BLOCKED_BY</span>
          </span>
          <span className="flex items-center space-x-1" title="Dotted steel edge">
            <span className="w-3 border-b-2 border-dotted border-steel-500 inline-block" />
            <span className="text-text-secondary">REQUIRES</span>
          </span>
        </div>
      </div>

      {/* Hero Ember Particles Drift */}
      <EmberSparks count={4} className="z-10" />

      {/* SVG Canvas Area */}
      <div
        className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing bg-bg-base transition-colors duration-200 overflow-hidden"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Soft Vignette Overlay */}
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_60%,rgba(110,150,180,0.12)_100%)] dark:bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(12,10,11,0.8)_100%)] z-10" />

        {/* Empty Graph State */}
        {!hasNodes && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center">
            {/* Ghost graph placeholder nodes */}
            <svg width="240" height="130" viewBox="0 0 240 130" className="opacity-40 mb-3" fill="none">
              <circle cx="50" cy="65" r="14" fill="#B3CDE0" stroke="#6F8FA8" strokeWidth="1.5" />
              <polygon points="120,35 136,65 120,95 104,65" fill="#CFE0EC" stroke="#6F8FA8" strokeWidth="1.5" />
              <circle cx="190" cy="65" r="14" fill="#E3EDF5" stroke="#6F8FA8" strokeWidth="1.5" />
              <line x1="64" y1="65" x2="104" y2="65" stroke="#6F8FA8" strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="136" y1="65" x2="176" y2="65" stroke="#6F8FA8" strokeWidth="1.5" />
            </svg>
            <p className="font-heading font-medium text-xs text-text-primary">
              Your graph appears as agents work
            </p>
            <p className="text-[11px] text-text-muted mt-0.5 max-w-xs">
              Autonomous agents build FalkorDB nodes and relationships in real-time as tasks execute.
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
        )}

        <svg className="w-full h-full">
          <defs>
            {/* Dotted Grid Pattern for Ice (soft white-blue) and Obsidian (dark ash) */}
            <pattern id="faintGrid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" fill="currentColor" className="text-steel-500/25 dark:text-steel-500/15" />
            </pattern>

            {/* Magma Gradient for Node */}
            <linearGradient id="magmaNodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFC93C" />
              <stop offset="45%" stopColor="#FF7A1A" />
              <stop offset="100%" stopColor="#E5301F" />
            </linearGradient>

            {/* Magma Glow Filter for Recommended Node */}
            <filter id="magmaGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Arrowhead Markers */}
            <marker id="arrowSteel" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(111, 143, 168, 0.6)" />
            </marker>
            <marker id="arrowLavaRed" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#E5301F" />
            </marker>
          </defs>

          {/* Background Grid */}
          <rect width="100%" height="100%" fill="url(#faintGrid)" />

          {/* Graph Transform Group */}
          {hasNodes && (
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Edges */}
              {edges.map((edge, idx) => {
                const src = nodePositions.get(edge.source);
                const tgt = nodePositions.get(edge.target);
                if (!src || !tgt) return null;

                const edgeType = (edge.type || '').toUpperCase();
                const isBlocked = edgeType.includes('BLOCK');
                const isRequires = edgeType.includes('REQUIRE');

                let strokeColor = 'rgba(111, 143, 168, 0.4)';
                let dashArray = 'none'; // DEPENDS_ON = solid
                let markerEnd = 'url(#arrowSteel)';

                if (isBlocked) {
                  strokeColor = '#E5301F';
                  dashArray = '6,3'; // BLOCKED_BY = dashed lava-red
                  markerEnd = 'url(#arrowLavaRed)';
                } else if (isRequires) {
                  strokeColor = '#6F8FA8';
                  dashArray = '2,3'; // REQUIRES = dotted steel
                  markerEnd = 'url(#arrowSteel)';
                }

                // Dim non-neighbor edges on hover
                const isEdgeHighlighted =
                  !neighborSet ||
                  (neighborSet.has(edge.source) && neighborSet.has(edge.target));

                return (
                  <g key={`edge-${edge.source}-${edge.target}-${idx}`} style={{ opacity: isEdgeHighlighted ? 1 : 0.15 }}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke={strokeColor}
                      strokeWidth={isBlocked ? 2 : 1.5}
                      strokeDasharray={dashArray}
                      markerEnd={markerEnd}
                      className="transition-all duration-300"
                    />
                    {(hoveredNodeId === edge.source || hoveredNodeId === edge.target) && (
                      <text
                        x={(src.x + tgt.x) / 2}
                        y={(src.y + tgt.y) / 2 - 4}
                        fill="#3E5A72"
                        fontSize="9"
                        fontFamily="JetBrains Mono, monospace"
                        textAnchor="middle"
                        className="select-none pointer-events-none"
                      >
                        {edge.type}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {nodes.map((node) => {
                const pos = nodePositions.get(node.id);
                if (!pos) return null;

                const isRecommended = recommendedTaskId === node.id;
                const matchesFilter =
                  activeFilter === 'ALL' ||
                  (node.type || '').toUpperCase().includes(activeFilter);

                // Neighbors stay bright, others dim to 25%
                const isNeighborOrFocal = !neighborSet || neighborSet.has(node.id);
                const nodeOpacity = !matchesFilter ? 0.15 : isNeighborOrFocal ? 1 : 0.25;

                return (
                  <g
                    key={node.id}
                    style={{ opacity: nodeOpacity }}
                    className="transition-opacity duration-300 cursor-pointer"
                    onClick={() => onSelectNode(node)}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                  >
                    {/* Pulsing Glow Ring for Recommended Task */}
                    {isRecommended && (
                      <g filter="url(#magmaGlow)">
                        <circle
                          cx={pos.x}
                          cy={pos.y}
                          r={34}
                          fill="none"
                          stroke="#FF7A1A"
                          strokeWidth={2}
                          className="animate-ping opacity-60"
                        />
                        <circle
                          cx={pos.x}
                          cy={pos.y}
                          r={28}
                          fill="none"
                          stroke="#FFC93C"
                          strokeWidth={1.5}
                          strokeDasharray="4,2"
                          className="animate-spin-slow opacity-80"
                        />
                      </g>
                    )}

                    {/* Node Shape */}
                    {renderNodeShape(node, pos, isRecommended)}

                    {/* Readiness Score Badge if Recommended */}
                    {isRecommended && readinessScore !== undefined && (
                      <g transform={`translate(${pos.x}, ${pos.y - 34})`}>
                        <rect
                          x="-38"
                          y="-10"
                          width="76"
                          height="18"
                          rx="9"
                          fill="#0C0A0B"
                          stroke="#FF7A1A"
                          strokeWidth="1.5"
                        />
                        <text
                          x="0"
                          y="3"
                          fill="#FFC93C"
                          fontSize="9"
                          fontWeight="bold"
                          fontFamily="JetBrains Mono, monospace"
                          textAnchor="middle"
                        >
                          SCORE {readinessScore}
                        </text>
                      </g>
                    )}

                    {/* Node Label */}
                    <text
                      x={pos.x}
                      y={pos.y + 30}
                      fill={isRecommended ? '#FF7A1A' : 'var(--text-primary)'}
                      fontSize="10"
                      fontWeight={isRecommended ? '600' : '500'}
                      textAnchor="middle"
                      className="select-none pointer-events-none drop-shadow-sm font-sans"
                    >
                      {node.label || node.id}
                    </text>
                  </g>
                );
              })}
            </g>
          )}
        </svg>

        {/* Floating Pan/Zoom Controls in Bottom-Right */}
        <div className="absolute bottom-20 right-3 z-20 flex flex-col items-center space-y-1 bg-surface/90 backdrop-blur-md border border-border-subtle p-1 rounded-lg shadow-md">
          <button
            onClick={() => setZoom((z) => Math.min(2.2, z + 0.2))}
            title="Zoom In"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 transition-colors"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
            title="Zoom Out"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 transition-colors"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={handleResetZoom}
            title="Recenter / Zoom to Fit"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 transition-colors"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Bottom: Reasoning Panel */}
      <div className="relative z-20 border-t border-border-subtle bg-surface/95 backdrop-blur-md p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
        {/* Typewriter Explanation Strip */}
        <div className="flex-1 min-w-0 flex items-center space-x-2">
          <div className="h-2 w-2 rounded-full bg-lava-orange shadow-[0_0_8px_rgba(255,122,26,0.8)] shrink-0 animate-pulse" />
          <p className="text-xs font-mono text-text-primary tracking-tight truncate leading-relaxed">
            {displayedReasoning}
            <span className="inline-block w-1.5 h-3 bg-lava-orange ml-1 animate-pulse" />
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2 shrink-0 relative">
          {/* Inject Blocker button */}
          <div className="relative">
            <button
              onClick={() => setIsBlockerPopoverOpen((v) => !v)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-steel-500" />
              <span>Inject Blocker</span>
            </button>

            {/* Confirmation Popover */}
            {isBlockerPopoverOpen && (
              <div className="absolute right-0 bottom-full mb-2 w-64 p-3 rounded-xl bg-surface border border-lava-red/40 shadow-xl z-50 animate-page-enter">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="h-4 w-4 text-lava-red shrink-0 mt-0.5" />
                  <div>
                    <h5 className="font-heading text-xs font-semibold text-text-primary">Inject Synthetic Blocker?</h5>
                    <p className="text-[11px] text-text-secondary mt-0.5 leading-snug">
                      Simulate a dependency blocker on {recommendedTaskId || 'the active task'} to demonstrate FalkorDB re-ranking.
                    </p>
                  </div>
                </div>
                <div className="flex justify-end space-x-2 mt-3 pt-2 border-t border-border-subtle">
                  <button
                    onClick={() => setIsBlockerPopoverOpen(false)}
                    className="px-2 py-1 text-[11px] rounded text-text-secondary hover:text-text-primary"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmInjectBlocker}
                    className="px-2.5 py-1 text-[11px] rounded bg-lava-red text-white font-medium hover:bg-lava-deep shadow-sm"
                  >
                    Confirm Inject
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Run FalkorDB Re-rank button (Primary Magma Button) */}
          <button
            onClick={handleRerankClick}
            disabled={isReranking}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg btn-magma text-xs font-semibold shadow-sm disabled:opacity-50"
          >
            {isReranking ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 fill-current" />
            )}
            <span>Run FalkorDB Re-rank</span>
          </button>
        </div>
      </div>
    </div>
  );
}
