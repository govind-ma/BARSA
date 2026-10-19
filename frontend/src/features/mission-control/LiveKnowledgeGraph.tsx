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
  Search,
  SlidersHorizontal,
  Eye,
  X,
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

  // Floating filter chips - default is "ALL"
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

  // Focus view mode (default: Focus on recommended task & 2-hop neighborhood)
  const [isFocusMode, setIsFocusMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('barsa_graph_focus_mode');
    return saved !== null ? saved === 'true' : true;
  });

  // Mini node search query
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Hovered node
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Legend popover state
  const [isLegendOpen, setIsLegendOpen] = useState(false);

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

  const toggleFocusMode = () => {
    setIsFocusMode((prev) => {
      const next = !prev;
      localStorage.setItem('barsa_graph_focus_mode', String(next));
      return next;
    });
  };

  // Node Degree Calculation
  const degreeMap = useMemo(() => {
    const map = new Map<string, number>();
    edges.forEach((e) => {
      map.set(e.source, (map.get(e.source) || 0) + 1);
      map.set(e.target, (map.get(e.target) || 0) + 1);
    });
    return map;
  }, [edges]);

  // Hub threshold: top 10% degree
  const hubDegreeThreshold = useMemo(() => {
    const degrees = Array.from(degreeMap.values()).sort((a, b) => b - a);
    if (degrees.length === 0) return 3;
    const top10Index = Math.floor(degrees.length * 0.1);
    return Math.max(3, degrees[top10Index] || 3);
  }, [degreeMap]);

  // Adjacency Map for 2-hop Focus View
  const adjacency = useMemo(() => {
    const adj = new Map<string, Set<string>>();
    edges.forEach((e) => {
      if (!adj.has(e.source)) adj.set(e.source, new Set());
      if (!adj.has(e.target)) adj.set(e.target, new Set());
      adj.get(e.source)!.add(e.target);
      adj.get(e.target)!.add(e.source);
    });
    return adj;
  }, [edges]);

  // Compute 2-hop focus neighborhood of recommended task
  const focusNodeIds = useMemo(() => {
    const focalId = recommendedTaskId || selectedNodeId || nodes[0]?.id;
    if (!focalId) return new Set<string>();

    const visited = new Set<string>([focalId]);
    let currentHop = new Set<string>([focalId]);

    // 2 hops
    for (let hop = 0; hop < 2; hop++) {
      const nextHop = new Set<string>();
      currentHop.forEach((id) => {
        const neighbors = adjacency.get(id);
        if (neighbors) {
          neighbors.forEach((nbr) => {
            if (!visited.has(nbr)) {
              visited.add(nbr);
              nextHop.add(nbr);
            }
          });
        }
      });
      currentHop = nextHop;
    }

    return visited;
  }, [recommendedTaskId, selectedNodeId, nodes, adjacency]);

  // Visible Nodes (Focus mode vs All mode, plus type filter)
  const visibleNodes = useMemo(() => {
    if (!nodes || nodes.length === 0) return [];

    let filtered = nodes;
    if (isFocusMode && nodes.length > 20) {
      filtered = filtered.filter((n) => focusNodeIds.has(n.id));
    }

    if (activeFilter !== 'ALL') {
      filtered = filtered.filter((n) => (n.type || '').toUpperCase().includes(activeFilter));
    }

    return filtered;
  }, [nodes, isFocusMode, focusNodeIds, activeFilter]);

  const visibleNodeIdSet = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

  // Visible Edges
  const visibleEdges = useMemo(() => {
    return edges.filter((e) => visibleNodeIdSet.has(e.source) && visibleNodeIdSet.has(e.target));
  }, [edges, visibleNodeIdSet]);

  // Cluster Centers for soft layout grouping
  const CLUSTER_CENTERS: Record<string, { x: number; y: number }> = {
    TASK: { x: 380, y: 240 },
    DECISION: { x: 200, y: 150 },
    CAPABILITY: { x: 190, y: 330 },
    AGENT: { x: 570, y: 160 },
    ISSUE: { x: 560, y: 340 },
  };

  // Node radius by type (task 8px, decision 10px, agent 12px, issue 9px, recommended 18px)
  const getNodeBaseRadius = (node: GraphNode, isRecommended: boolean) => {
    if (isRecommended) return 18;
    const type = (node.type || 'TASK').toUpperCase();
    if (type.includes('DECISION')) return 10;
    if (type.includes('AGENT')) return 12;
    if (type.includes('ISSUE') || type.includes('BLOCKER')) return 9;
    if (type.includes('CAPABILITY')) return 10;
    return 8; // Task
  };

  // Compute Layout once, frozen (force simulation with collision avoidance)
  const nodePositions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    if (visibleNodes.length === 0) return map;

    // Initial positioning based on cluster center + slight deterministic jitter
    visibleNodes.forEach((node, i) => {
      const type = (node.type || 'TASK').toUpperCase();
      let key = 'TASK';
      if (type.includes('DECISION')) key = 'DECISION';
      else if (type.includes('AGENT')) key = 'AGENT';
      else if (type.includes('ISSUE') || type.includes('BLOCKER')) key = 'ISSUE';
      else if (type.includes('CAPABILITY')) key = 'CAPABILITY';

      const center = CLUSTER_CENTERS[key] || { x: 380, y: 240 };
      const angle = (i * 2.39996) % (2 * Math.PI); // Golden angle
      const spread = 20 + Math.sqrt(i) * 18;

      if (recommendedTaskId && node.id === recommendedTaskId) {
        map.set(node.id, { x: 380, y: 240 });
      } else {
        map.set(node.id, {
          x: center.x + Math.cos(angle) * spread,
          y: center.y + Math.sin(angle) * spread,
        });
      }
    });

    // 40 Force Simulation iterations for collision relaxation & spring links
    const nodeArray = visibleNodes.map((n) => ({
      id: n.id,
      r: getNodeBaseRadius(n, n.id === recommendedTaskId),
      x: map.get(n.id)!.x,
      y: map.get(n.id)!.y,
      vx: 0,
      vy: 0,
    }));

    const nodeIndex = new Map(nodeArray.map((d, idx) => [d.id, idx]));

    for (let iter = 0; iter < 45; iter++) {
      // 1. Collision avoidance (node radius + 12px)
      for (let i = 0; i < nodeArray.length; i++) {
        for (let j = i + 1; j < nodeArray.length; j++) {
          const a = nodeArray[i];
          const b = nodeArray[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const minDist = a.r + b.r + 14;

          if (dist < minDist) {
            const overlap = (minDist - dist) / dist * 0.5;
            const ox = dx * overlap;
            const oy = dy * overlap;
            if (a.id !== recommendedTaskId) {
              a.x -= ox;
              a.y -= oy;
            }
            if (b.id !== recommendedTaskId) {
              b.x += ox;
              b.y += oy;
            }
          }
        }
      }

      // 2. Link attraction
      visibleEdges.forEach((e) => {
        const uIdx = nodeIndex.get(e.source);
        const vIdx = nodeIndex.get(e.target);
        if (uIdx !== undefined && vIdx !== undefined) {
          const u = nodeArray[uIdx];
          const v = nodeArray[vIdx];
          const dx = v.x - u.x;
          const dy = v.y - u.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const targetDist = 65;
          const force = (dist - targetDist) * 0.03;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (u.id !== recommendedTaskId) {
            u.x += fx;
            u.y += fy;
          }
          if (v.id !== recommendedTaskId) {
            v.x -= fx;
            v.y -= fy;
          }
        }
      });
    }

    // Freeze positions into output map
    nodeArray.forEach((n) => {
      map.set(n.id, { x: Math.round(n.x), y: Math.round(n.y) });
    });

    return map;
  }, [visibleNodes, visibleEdges, recommendedTaskId]);

  // Neighbor map for hover brightening (neighbors stay bright, others dim)
  const neighborSet = useMemo(() => {
    const targetId = hoveredNodeId || highlightedNodeId || selectedNodeId;
    if (!targetId) return null;
    const set = new Set<string>([targetId]);
    edges.forEach((e) => {
      if (e.source === targetId) set.add(e.target);
      if (e.target === targetId) set.add(e.source);
    });
    return set;
  }, [hoveredNodeId, highlightedNodeId, selectedNodeId, edges]);

  // Label collision detection & placement algorithm
  const renderedLabels = useMemo(() => {
    const placedBoxes: { x: number; y: number; w: number; h: number }[] = [];
    const labelsToRender: {
      nodeId: string;
      x: number;
      y: number;
      text: string;
      fullText: string;
      pillWidth: number;
      pillHeight: number;
      isRecommended: boolean;
    }[] = [];

    visibleNodes.forEach((node) => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;

      const isRecommended = recommendedTaskId === node.id;
      const isSelected = selectedNodeId === node.id;
      const isHovered = hoveredNodeId === node.id || (hoveredNodeId && neighborSet?.has(node.id));
      const degree = degreeMap.get(node.id) || 0;
      const isHub = degree >= hubDegreeThreshold;

      // Rule: show label ONLY for recommended, selected, hovered/neighbors, or above LOD threshold
      let shouldShowLabel = false;
      if (isRecommended || isSelected || isHovered) {
        shouldShowLabel = true;
      } else if (zoom >= 2.0) {
        shouldShowLabel = true; // Zoom > 2: show all
      } else if (zoom >= 1.2 && isHub) {
        shouldShowLabel = true; // Zoom 1.2-2.0: show hubs
      }

      if (!shouldShowLabel) return;

      const rawTitle = node.label || node.id || 'Node';
      const text = rawTitle.length > 28 ? rawTitle.slice(0, 25) + '...' : rawTitle;
      const r = getNodeBaseRadius(node, isRecommended);

      // Estimate pill dimensions
      const pillWidth = Math.max(48, Math.min(220, text.length * 6.8 + 16));
      const pillHeight = 20;
      const pillX = pos.x - pillWidth / 2;
      const pillY = pos.y + r + 6;

      // Collision test with already placed boxes
      const collides = placedBoxes.some((box) => {
        return (
          pillX < box.x + box.w &&
          pillX + pillWidth > box.x &&
          pillY < box.y + box.h &&
          pillY + pillHeight > box.y
        );
      });

      // Always show recommended & selected regardless of collision; otherwise skip colliding
      if (collides && !isRecommended && !isSelected && !isHovered) {
        return;
      }

      placedBoxes.push({ x: pillX, y: pillY, w: pillWidth, h: pillHeight });
      labelsToRender.push({
        nodeId: node.id,
        x: pos.x,
        y: pillY,
        text,
        fullText: rawTitle,
        pillWidth,
        pillHeight,
        isRecommended,
      });
    });

    return labelsToRender;
  }, [visibleNodes, nodePositions, zoom, recommendedTaskId, selectedNodeId, hoveredNodeId, neighborSet, degreeMap, hubDegreeThreshold]);

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button, input, .no-pan')) return;
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

  // Center on a searched node
  const handleSelectSearchMatch = (nodeId: string) => {
    const pos = nodePositions.get(nodeId);
    if (pos) {
      setPan({ x: 380 - pos.x, y: 240 - pos.y });
      setZoom(1.4);
      const targetNode = nodes.find((n) => n.id === nodeId) || null;
      onSelectNode(targetNode);
      setIsSearchOpen(false);
      setSearchQuery('');
    }
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

  // Node Shape Renderer (scaled sizes: Task 8px, Decision 10px, Agent 12px, Issue 9px, Recommended 18px)
  const renderNodeShape = (node: GraphNode, pos: { x: number; y: number }, isRecommended: boolean) => {
    const type = (node.type || 'Task').toUpperCase();
    const isHovered = hoveredNodeId === node.id || highlightedNodeId === node.id;
    const isSelected = selectedNodeId === node.id;
    const degree = degreeMap.get(node.id) || 0;
    const degreeScale = Math.min(1.8, 1 + degree * 0.08);

    if (isRecommended) {
      return (
        <g>
          <circle
            cx={pos.x}
            cy={pos.y}
            r={18}
            fill="url(#magmaNodeGrad)"
            stroke="#FFFFFF"
            strokeWidth={2}
            className={`transition-all duration-300 ${justReranked ? 'filter drop-shadow-[0_0_20px_rgba(255,122,26,0.9)] scale-110' : 'filter drop-shadow-[0_0_12px_rgba(255,122,26,0.6)]'}`}
          />
          <circle cx={pos.x} cy={pos.y} r={12} fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth={1.2} />
        </g>
      );
    }

    if (type.includes('DECISION')) {
      // Decision = lava-yellow hexagon (radius 10px)
      const r = 10 * degreeScale;
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
          stroke={isSelected ? '#0D1A24' : isHovered ? '#FFFFFF' : '#FF7A1A'}
          strokeWidth={isSelected ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_6px_rgba(255,201,60,0.35)]"
        />
      );
    }

    if (type.includes('CAPABILITY')) {
      // Capability = ice-300 rounded square (size 18px)
      const size = 18 * degreeScale;
      return (
        <rect
          x={pos.x - size / 2}
          y={pos.y - size / 2}
          width={size}
          height={size}
          rx={4}
          fill="#B3CDE0"
          stroke={isSelected ? '#0D1A24' : '#6F8FA8'}
          strokeWidth={isSelected ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_6px_rgba(179,205,224,0.3)]"
        />
      );
    }

    if (type.includes('AGENT')) {
      // Agent = lava-orange diamond (radius 12px)
      const d = 12 * degreeScale;
      const points = `${pos.x},${pos.y - d} ${pos.x + d},${pos.y} ${pos.x},${pos.y + d} ${pos.x - d},${pos.y}`;
      return (
        <polygon
          points={points}
          fill="#FF7A1A"
          stroke={isSelected ? '#FFFFFF' : '#E5301F'}
          strokeWidth={isSelected ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(255,122,26,0.4)]"
        />
      );
    }

    if (type.includes('ISSUE') || type.includes('BLOCKER')) {
      // Issue = lava-red circle (radius 9px)
      const r = 9 * degreeScale;
      return (
        <circle
          cx={pos.x}
          cy={pos.y}
          r={r}
          fill="#E5301F"
          stroke={isSelected ? '#FFFFFF' : '#A81414'}
          strokeWidth={isSelected ? 2.5 : 1.5}
          className="transition-all duration-200 filter drop-shadow-[0_0_8px_rgba(229,48,31,0.5)]"
        />
      );
    }

    // Default: Task (steel-500 circle 8px)
    const r = 8 * degreeScale;
    return (
      <circle
        cx={pos.x}
        cy={pos.y}
        r={r}
        fill="#6F8FA8"
        stroke={isSelected ? '#FF7A1A' : isHovered ? '#FFFFFF' : '#3E5A72'}
        strokeWidth={isSelected ? 2.5 : 1.5}
        className="transition-all duration-200 filter drop-shadow-[0_0_6px_rgba(111,143,168,0.3)]"
      />
    );
  };

  const hasNodes = visibleNodes.length > 0;

  return (
    <div className="relative flex flex-col h-full glass-card overflow-hidden shadow-md select-none">
      {/* Lava line sweep during FalkorDB Re-rank */}
      {isReranking && (
        <div className="absolute top-0 left-0 right-0 h-1 z-30 overflow-hidden bg-ice-100">
          <div className="h-full w-1/3 bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red animate-lavaSweep shadow-[0_0_12px_rgba(255,122,26,0.8)]" />
        </div>
      )}

      {/* ======================================================== */}
      {/* TOP-LEFT OVERLAY: Single-row Horizontal Filter Chips    */}
      {/* ======================================================== */}
      <div className="absolute top-3 left-3 z-graph-overlay max-w-[calc(100%-180px)] pointer-events-none">
        <div className="flex items-center space-x-1 p-1 rounded-lg solid-floating-surface pointer-events-auto overflow-x-auto whitespace-nowrap no-scrollbar">
          {FILTER_PILLS.map((chip) => {
            const isActive = activeFilter === chip.id;
            return (
              <button
                key={chip.id}
                onClick={() => setActiveFilter(chip.id)}
                className={`relative text-[11px] font-mono px-2.5 py-1 rounded-md transition-all duration-150 shrink-0 ${
                  isActive
                    ? 'bg-ice-100 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs border border-border-strong'
                    : 'text-text-muted hover:text-text-primary hover:bg-ice-100/60 dark:hover:bg-white/[0.04]'
                }`}
              >
                {chip.label}
                {isActive && (
                  <span className="absolute bottom-0 left-1 right-1 h-0.5 rounded-full bg-gradient-to-r from-lava-yellow to-lava-orange" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ======================================================== */}
      {/* TOP-RIGHT OVERLAY: Focus / All Toggle & Mini Node Search */}
      {/* ======================================================== */}
      <div className="absolute top-3 right-3 z-graph-overlay flex items-center space-x-2 pointer-events-none">
        {/* Search button / input */}
        <div className="relative pointer-events-auto">
          {isSearchOpen ? (
            <div className="flex items-center space-x-1.5 p-1 rounded-lg solid-floating-surface shadow-md animate-in fade-in">
              <Search className="h-3.5 w-3.5 text-text-muted ml-1.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Find a node..."
                className="bg-transparent text-xs font-mono text-text-primary focus:outline-none w-32 placeholder:text-text-muted"
                autoFocus
              />
              <button
                onClick={() => {
                  setIsSearchOpen(false);
                  setSearchQuery('');
                }}
                className="p-1 rounded text-text-muted hover:text-text-primary"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsSearchOpen(true)}
              title="Search and center node"
              className="p-2 rounded-lg solid-floating-surface text-text-muted hover:text-text-primary transition-colors shadow-xs"
            >
              <Search className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Search Dropdown Results */}
          {isSearchOpen && searchQuery.trim() && (
            <div className="absolute right-0 top-full mt-1.5 w-60 max-h-48 overflow-y-auto solid-floating-surface rounded-lg p-1.5 space-y-1 shadow-xl z-popover">
              {nodes
                .filter((n) => (n.label || n.id).toLowerCase().includes(searchQuery.toLowerCase()))
                .slice(0, 6)
                .map((match) => (
                  <button
                    key={match.id}
                    onClick={() => handleSelectSearchMatch(match.id)}
                    className="w-full text-left px-2 py-1.5 rounded text-xs truncate hover:bg-ice-100 dark:hover:bg-bg-elevated transition-colors flex items-center justify-between"
                  >
                    <span className="truncate">{match.label || match.id}</span>
                    <span className="text-[9px] font-mono uppercase text-text-muted ml-1.5 shrink-0">
                      {match.type}
                    </span>
                  </button>
                ))}
            </div>
          )}
        </div>

        {/* Focus Mode Pill Toggle */}
        <button
          onClick={toggleFocusMode}
          title={isFocusMode ? 'Switch to All Nodes view' : 'Switch to Focus Neighborhood view'}
          className={`pointer-events-auto flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all solid-floating-surface shadow-xs ${
            isFocusMode
              ? 'border-lava-orange/40 text-lava-orange'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Eye className="h-3.5 w-3.5 text-lava-orange" />
          <span>
            {isFocusMode
              ? `Focus (${visibleNodes.length}/${nodes.length})`
              : `All (${nodes.length})`}
          </span>
        </button>
      </div>

      {/* ======================================================== */}
      {/* BOTTOM-LEFT OVERLAY: Collapsed Legend Popover Button     */}
      {/* ======================================================== */}
      <div className="absolute bottom-20 left-3 z-graph-overlay pointer-events-none">
        <div className="relative pointer-events-auto">
          <button
            onClick={() => setIsLegendOpen((prev) => !prev)}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg solid-floating-surface text-xs font-mono text-text-secondary hover:text-text-primary shadow-xs transition-colors"
          >
            <SlidersHorizontal className="h-3.5 w-3.5 text-steel-500" />
            <span>Legend</span>
          </button>

          {/* Solid Legend Popover */}
          {isLegendOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-52 p-3 rounded-xl solid-floating-surface shadow-xl z-popover space-y-2 animate-page-enter">
              <div className="flex items-center justify-between border-b border-border-subtle pb-1.5">
                <span className="text-[10px] font-mono uppercase text-text-muted font-bold tracking-wider">
                  Edge Relationships
                </span>
                <button
                  onClick={() => setIsLegendOpen(false)}
                  className="p-0.5 text-text-muted hover:text-text-primary"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>

              <div className="space-y-1.5 text-[11px] font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">DEPENDS_ON</span>
                  <span className="w-8 border-b-2 border-steel-500 inline-block opacity-70" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-lava-red">BLOCKED_BY</span>
                  <span className="w-8 border-b-2 border-dashed border-lava-red inline-block" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">REQUIRES</span>
                  <span className="w-8 border-b-2 border-dotted border-steel-500 inline-block" />
                </div>
              </div>

              <div className="pt-2 border-t border-border-subtle grid grid-cols-2 gap-1.5 text-[10px] font-mono text-text-muted">
                <div className="flex items-center space-x-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-steel-500" />
                  <span>Task</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-2.5 h-2.5 bg-lava-yellow rotate-45" />
                  <span>Decision</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-2.5 h-2.5 bg-lava-orange rotate-45" />
                  <span>Agent</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-ice-300" />
                  <span>Capability</span>
                </div>
              </div>
            </div>
          )}
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
            {/* Dotted Grid Pattern for Ice & Obsidian - Soft & Unobtrusive */}
            <pattern id="faintGrid" width="28" height="28" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="0.75" fill="currentColor" className="text-steel-500/10 dark:text-steel-500/5" />
            </pattern>

            {/* Magma Gradient for Recommended Node */}
            <linearGradient id="magmaNodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFC93C" />
              <stop offset="45%" stopColor="#FF7A1A" />
              <stop offset="100%" stopColor="#E5301F" />
            </linearGradient>

            {/* Glow Filter for Recommended Task */}
            <filter id="magmaGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Arrowhead Markers */}
            <marker id="arrowSteel" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(111, 143, 168, 0.6)" />
            </marker>
            <marker id="arrowLavaRed" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#E5301F" />
            </marker>
          </defs>

          {/* Background Grid */}
          <rect width="100%" height="100%" fill="url(#faintGrid)" />

          {/* Graph Transform Group */}
          {hasNodes && (
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Edges (1px width, 25% default opacity, 90% on hover, 8% otherwise) */}
              {visibleEdges.map((edge, idx) => {
                const src = nodePositions.get(edge.source);
                const tgt = nodePositions.get(edge.target);
                if (!src || !tgt) return null;

                const edgeType = (edge.type || '').toUpperCase();
                const isBlocked = edgeType.includes('BLOCK');
                const isRequires = edgeType.includes('REQUIRE');

                let strokeColor = 'rgba(111, 143, 168, 0.5)';
                let dashArray = 'none'; // DEPENDS_ON = solid
                let markerEnd = 'url(#arrowSteel)';

                if (isBlocked) {
                  strokeColor = '#E5301F';
                  dashArray = '5,3'; // BLOCKED_BY = dashed lava-red
                  markerEnd = 'url(#arrowLavaRed)';
                } else if (isRequires) {
                  strokeColor = '#6F8FA8';
                  dashArray = '2,3'; // REQUIRES = dotted steel
                  markerEnd = 'url(#arrowSteel)';
                }

                // Connected edge check
                const isEdgeConnected =
                  hoveredNodeId === edge.source ||
                  hoveredNodeId === edge.target ||
                  selectedNodeId === edge.source ||
                  selectedNodeId === edge.target;

                const hasActiveSelection = Boolean(hoveredNodeId || selectedNodeId);
                const edgeOpacity = isEdgeConnected ? 0.9 : hasActiveSelection ? 0.08 : 0.25;

                return (
                  <g key={`edge-${edge.source}-${edge.target}-${idx}`} style={{ opacity: edgeOpacity }}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke={strokeColor}
                      strokeWidth={1}
                      strokeDasharray={dashArray}
                      markerEnd={markerEnd}
                      className="transition-opacity duration-300"
                    />
                  </g>
                );
              })}

              {/* Nodes */}
              {visibleNodes.map((node) => {
                const pos = nodePositions.get(node.id);
                if (!pos) return null;

                const isRecommended = recommendedTaskId === node.id;
                const isNeighborOrFocal = !neighborSet || neighborSet.has(node.id);
                const hasFocusFilter = Boolean(hoveredNodeId || selectedNodeId);
                const nodeOpacity = !hasFocusFilter ? 1 : isNeighborOrFocal ? 1 : 0.25;

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
                          r={26}
                          fill="none"
                          stroke="#FF7A1A"
                          strokeWidth={1.5}
                          className="animate-ping opacity-60"
                        />
                      </g>
                    )}

                    {/* Node Shape */}
                    {renderNodeShape(node, pos, isRecommended)}

                    {/* Readiness Score Badge for Recommended Node */}
                    {isRecommended && readinessScore !== undefined && (
                      <g transform={`translate(${pos.x}, ${pos.y - 26})`}>
                        <rect
                          x="-32"
                          y="-9"
                          width="64"
                          height="16"
                          rx="8"
                          fill="#0C0A0B"
                          stroke="#FF7A1A"
                          strokeWidth={1.2}
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
                  </g>
                );
              })}

              {/* Collision-avoided Pill Labels Layer */}
              {renderedLabels.map((item) => (
                <g key={`lbl-${item.nodeId}`} className="pointer-events-none select-none transition-all duration-200">
                  {/* Semi-opaque pill background */}
                  <rect
                    x={item.x - item.pillWidth / 2}
                    y={item.y}
                    width={item.pillWidth}
                    height={item.pillHeight}
                    rx={6}
                    className="fill-surface/95 dark:fill-bg-elevated/95 stroke-border-subtle"
                    strokeWidth={1}
                  />
                  <text
                    x={item.x}
                    y={item.y + 13.5}
                    fill={item.isRecommended ? '#FF7A1A' : 'var(--text-primary)'}
                    fontSize="11"
                    fontWeight={item.isRecommended ? '600' : '500'}
                    fontFamily="Inter, sans-serif"
                    textAnchor="middle"
                  >
                    {item.text}
                  </text>
                </g>
              ))}
            </g>
          )}
        </svg>

        {/* ======================================================== */}
        {/* BOTTOM-RIGHT OVERLAY: Pan/Zoom Controls                  */}
        {/* ======================================================== */}
        <div className="absolute bottom-20 right-3 z-graph-overlay flex flex-col items-center space-y-1 solid-floating-surface p-1 rounded-lg shadow-md">
          <button
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.25))}
            title="Zoom In"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 dark:hover:bg-bg-elevated transition-colors"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.25))}
            title="Zoom Out"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 dark:hover:bg-bg-elevated transition-colors"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={handleResetZoom}
            title="Recenter / Zoom to Fit"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 dark:hover:bg-bg-elevated transition-colors"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* ======================================================== */}
      {/* BOTTOM: Firmly Docked Reasoning Panel                   */}
      {/* ======================================================== */}
      <div className="relative z-base border-t border-border-subtle bg-surface px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
        {/* Typewriter Explanation Strip */}
        <div className="flex-1 min-w-0 flex items-center space-x-2">
          <div className="h-2 w-2 rounded-full bg-lava-orange shadow-[0_0_8px_rgba(255,122,26,0.8)] shrink-0 animate-pulse" />
          <p className="text-xs font-mono text-text-primary tracking-tight truncate leading-relaxed">
            {displayedReasoning}
            <span className="inline-block w-1.5 h-3 bg-lava-orange ml-1 animate-pulse" />
          </p>
        </div>

        {/* Action Buttons: 1 Primary + 1 Secondary */}
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
              <div className="absolute right-0 bottom-full mb-2 w-64 p-3 rounded-xl solid-floating-surface border-lava-red/40 shadow-xl z-popover animate-page-enter">
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
              <Play className="h-3.5 w-3.5 fill-current text-white" />
            )}
            <span>Run FalkorDB Re-rank</span>
          </button>
        </div>
      </div>
    </div>
  );
}
