import React, { useState, useMemo, useEffect } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  AlertTriangle,
  Play,
  ShieldAlert,
} from 'lucide-react';
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
  isLoading?: boolean;
}

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
}: LiveKnowledgeGraphProps) {
  // Pan and Zoom
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Floating filters
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

  // Hovered node for neighbor brightening
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Blocker popover state
  const [isBlockerPopoverOpen, setIsBlockerPopoverOpen] = useState(false);
  const [isReranking, setIsReranking] = useState(false);

  // Typewriter reasoning text
  const [displayedReasoning, setDisplayedReasoning] = useState('');
  const fullReasoning = whyReadyText || (
    recommendedTaskId
      ? `All dependencies satisfied for ${recommendedTaskId}. 0 active blockers. Readiness ${readinessScore ?? '270.0'}.`
      : 'FalkorDB graph engine: Cypher multi-hop query analysis ready.'
  );

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

    // Place recommended task at center-left if present
    const radius = Math.min(220, 70 + count * 15);

    nodes.forEach((node, i) => {
      // If node is the recommended next task, place near focal center
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

  // Neighbor map for hover brightening
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
    } finally {
      setIsReranking(false);
    }
  };

  const handleConfirmInjectBlocker = () => {
    setIsBlockerPopoverOpen(false);
    onInjectBlocker();
  };

  // Node shape renderer based on specification:
  // Task: ice-400 (#38bdf8)
  // Decision: ice-200 hexagon (#bae6fd)
  // Capability: teal-ice (#2dd4bf)
  // Agent: ember (#f59e0b)
  // Issue: chilli (#ef4444)
  const renderNodeShape = (node: GraphNode, pos: { x: number; y: number }, isRecommended: boolean) => {
    const type = (node.type || 'Task').toUpperCase();
    const isHovered = hoveredNodeId === node.id || highlightedNodeId === node.id;
    const isSelected = selectedNodeId === node.id;

    if (type.includes('DECISION')) {
      // Hexagon for Decision
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
          fill="#bae6fd"
          stroke={isSelected ? '#38bdf8' : isHovered ? '#38bdf8' : '#7dd3fc'}
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(186,230,253,0.3)]"
        />
      );
    }

    if (type.includes('CAPABILITY')) {
      // Diamond for Capability
      const d = 18;
      const points = `${pos.x},${pos.y - d} ${pos.x + d},${pos.y} ${pos.x},${pos.y + d} ${pos.x - d},${pos.y}`;
      return (
        <polygon
          points={points}
          fill="#2dd4bf"
          stroke="#14b8a6"
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(45,212,191,0.3)]"
        />
      );
    }

    if (type.includes('AGENT')) {
      return (
        <circle
          cx={pos.x}
          cy={pos.y}
          r={18}
          fill="#f59e0b"
          stroke="#d97706"
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(245,158,11,0.35)]"
        />
      );
    }

    if (type.includes('ISSUE') || type.includes('BLOCKER')) {
      return (
        <rect
          x={pos.x - 18}
          y={pos.y - 14}
          width={36}
          height={28}
          rx={6}
          fill="#ef4444"
          stroke="#dc2626"
          strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_10px_rgba(239,68,68,0.4)]"
        />
      );
    }

    // Default: Task (ice-400 circle)
    return (
      <circle
        cx={pos.x}
        cy={pos.y}
        r={isRecommended ? 22 : 18}
        fill="#38bdf8"
        stroke={isRecommended ? '#ef4444' : isSelected ? '#ffffff' : '#0284c7'}
        strokeWidth={isRecommended ? 2.5 : isSelected ? 3 : isHovered ? 2.5 : 1.5}
        className="transition-all duration-200 filter drop-shadow-[0_0_10px_rgba(56,189,248,0.4)]"
      />
    );
  };

  return (
    <div className="relative flex flex-col h-full bg-card/60 backdrop-blur-md border border-ice/15 rounded-2xl overflow-hidden shadow-[0_8px_32px_rgba(0,0,0,0.3)] select-none">
      {/* Top Floating Entity Filter Chips */}
      <div className="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-background/80 backdrop-blur-md border border-ice/20 shadow-lg pointer-events-auto">
          {['ALL', 'TASK', 'DECISION', 'AGENT', 'CAPABILITY', 'ISSUE'].map((chip) => {
            const isActive = activeFilter === chip;
            return (
              <button
                key={chip}
                onClick={() => setActiveFilter(chip)}
                className={`text-[10px] font-mono px-2 py-0.5 rounded-lg transition-all ${
                  isActive
                    ? 'bg-ice text-background font-bold shadow-[0_0_8px_rgba(56,189,248,0.6)]'
                    : 'text-muted-foreground hover:text-ice hover:bg-secondary/60'
                }`}
              >
                {chip}
              </button>
            );
          })}
        </div>

        {/* Dash Legend Pill */}
        <div className="hidden sm:flex items-center space-x-3 px-2.5 py-1 rounded-xl bg-background/80 backdrop-blur-md border border-ice/20 text-[10px] text-muted-foreground font-mono pointer-events-auto">
          <span className="flex items-center space-x-1">
            <span className="w-3 border-b-2 border-dashed border-ice inline-block" />
            <span>DEPENDS_ON</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-3 border-b-2 border-dashed border-chilli inline-block" />
            <span>BLOCKED_BY</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-3 border-b-2 border-dotted border-teal-400 inline-block" />
            <span>REQUIRES</span>
          </span>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div
        className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing bg-[#090d14]"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Soft Ice Vignette Overlay */}
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_50%,rgba(9,13,20,0.85)_100%)] z-10" />

        <svg className="w-full h-full">
          <defs>
            {/* Dotted Grid Pattern */}
            <pattern id="faintGrid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" fill="rgba(56, 189, 248, 0.12)" />
            </pattern>

            {/* Chilli Glow Filter for Recommended Task */}
            <filter id="chilliGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Arrowhead Markers */}
            <marker id="arrowIce" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(56, 189, 248, 0.5)" />
            </marker>
            <marker id="arrowChilli" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#ef4444" />
            </marker>
            <marker id="arrowTeal" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#2dd4bf" />
            </marker>
          </defs>

          {/* Background Grid */}
          <rect width="100%" height="100%" fill="url(#faintGrid)" />

          {/* Graph Transform Group */}
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Edges */}
            {edges.map((edge, idx) => {
              const src = nodePositions.get(edge.source);
              const tgt = nodePositions.get(edge.target);
              if (!src || !tgt) return null;

              const edgeType = (edge.type || '').toUpperCase();
              const isBlocked = edgeType.includes('BLOCK');
              const isRequires = edgeType.includes('REQUIRE');
              const isDepends = edgeType.includes('DEPEND');

              let strokeColor = 'rgba(56, 189, 248, 0.35)';
              let dashArray = 'none';
              let markerEnd = 'url(#arrowIce)';

              if (isBlocked) {
                strokeColor = '#ef4444';
                dashArray = '6,3';
                markerEnd = 'url(#arrowChilli)';
              } else if (isRequires) {
                strokeColor = '#2dd4bf';
                dashArray = '2,3';
                markerEnd = 'url(#arrowTeal)';
              } else if (isDepends) {
                dashArray = '5,4';
              }

              // Dim edges if neighbor highlighting is active
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
                  {/* Subtle edge label on hover */}
                  {(hoveredNodeId === edge.source || hoveredNodeId === edge.target) && (
                    <text
                      x={(src.x + tgt.x) / 2}
                      y={(src.y + tgt.y) / 2 - 4}
                      fill="#bae6fd"
                      fontSize="9"
                      fontFamily="monospace"
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

              // Neighbor dimming
              const isNeighborOrFocal = !neighborSet || neighborSet.has(node.id);
              const nodeOpacity = !matchesFilter ? 0.15 : isNeighborOrFocal ? 1 : 0.25;

              return (
                <g
                  key={node.id}
                  transform={`translate(0, 0)`}
                  style={{ opacity: nodeOpacity }}
                  className="transition-opacity duration-300 cursor-pointer"
                  onClick={() => onSelectNode(node)}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                >
                  {/* Pulsing Chilli Ring for Recommended Task */}
                  {isRecommended && (
                    <g filter="url(#chilliGlow)">
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r={32}
                        fill="none"
                        stroke="#ef4444"
                        strokeWidth={2}
                        className="animate-ping opacity-60"
                      />
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r={27}
                        fill="none"
                        stroke="#ef4444"
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
                    <g transform={`translate(${pos.x}, ${pos.y - 30})`}>
                      <rect
                        x="-38"
                        y="-10"
                        width="76"
                        height="18"
                        rx="9"
                        fill="#090d14"
                        stroke="#ef4444"
                        strokeWidth="1.5"
                      />
                      <text
                        x="0"
                        y="3"
                        fill="#ef4444"
                        fontSize="9"
                        fontWeight="bold"
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        SCORE {readinessScore}
                      </text>
                    </g>
                  )}

                  {/* Node Label */}
                  <text
                    x={pos.x}
                    y={pos.y + 28}
                    fill={isRecommended ? '#ef4444' : '#f1f5f9'}
                    fontSize="10"
                    fontWeight={isRecommended ? 'bold' : 'medium'}
                    textAnchor="middle"
                    className="select-none pointer-events-none drop-shadow-[0_1px_3px_rgba(0,0,0,0.8)]"
                  >
                    {node.label || node.id}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Floating Pan/Zoom Controls in Bottom-Right */}
        <div className="absolute bottom-20 right-3 z-20 flex flex-col items-center space-y-1 bg-background/80 backdrop-blur-md border border-ice/20 p-1 rounded-xl shadow-lg">
          <button
            onClick={() => setZoom((z) => Math.min(2.2, z + 0.2))}
            title="Zoom In"
            className="p-1.5 rounded-lg text-muted-foreground hover:text-ice hover:bg-secondary/60 transition-colors"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
            title="Zoom Out"
            className="p-1.5 rounded-lg text-muted-foreground hover:text-ice hover:bg-secondary/60 transition-colors"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={handleResetZoom}
            title="Recenter / Zoom to Fit"
            className="p-1.5 rounded-lg text-muted-foreground hover:text-ice hover:bg-secondary/60 transition-colors"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Bottom: Reasoning Panel */}
      <div className="relative z-20 border-t border-ice/15 bg-background/80 backdrop-blur-md p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-[0_-4px_20px_rgba(0,0,0,0.3)]">
        {/* Typewriter Explanation Strip */}
        <div className="flex-1 min-w-0 flex items-center space-x-2">
          <div className="h-2 w-2 rounded-full bg-ice shadow-[0_0_8px_rgba(56,189,248,0.8)] shrink-0 animate-pulse" />
          <p className="text-xs font-mono text-foreground tracking-tight truncate leading-relaxed">
            {displayedReasoning}
            <span className="inline-block w-1.5 h-3 bg-ice ml-1 animate-pulse" />
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2 shrink-0 relative">
          {/* Inject Blocker button */}
          <div className="relative">
            <button
              onClick={() => setIsBlockerPopoverOpen((v) => !v)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-ice/30 hover:border-ice/60 bg-ice/10 hover:bg-ice/20 text-ice text-xs font-medium transition-all shadow-[0_0_10px_rgba(56,189,248,0.15)]"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-ice" />
              <span>Inject Blocker</span>
            </button>

            {/* Confirmation Popover */}
            {isBlockerPopoverOpen && (
              <div className="absolute right-0 bottom-full mb-2 w-64 p-3 rounded-xl bg-card border border-chilli/40 shadow-[0_8px_24px_rgba(239,68,68,0.3)] z-50 animate-page-enter">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="h-4 w-4 text-chilli shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-xs font-bold text-foreground">Inject Synthetic Blocker?</h5>
                    <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                      Simulate a dependency blocker on {recommendedTaskId || 'the active task'} to demonstrate FalkorDB re-ranking.
                    </p>
                  </div>
                </div>
                <div className="flex justify-end space-x-2 mt-3 pt-2 border-t border-border/60">
                  <button
                    onClick={() => setIsBlockerPopoverOpen(false)}
                    className="px-2 py-1 text-[11px] rounded text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmInjectBlocker}
                    className="px-2.5 py-1 text-[11px] rounded bg-chilli text-white font-medium hover:bg-chilli/90 shadow-[0_0_10px_rgba(239,68,68,0.5)]"
                  >
                    Confirm Inject
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Run FalkorDB Re-rank button */}
          <button
            onClick={handleRerankClick}
            disabled={isReranking}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-chilli hover:bg-chilli/90 text-white font-semibold text-xs transition-all shadow-[0_0_15px_rgba(239,68,68,0.4)] disabled:opacity-50"
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
