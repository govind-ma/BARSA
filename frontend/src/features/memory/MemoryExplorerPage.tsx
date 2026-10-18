import { useEffect, useState, useRef, useMemo } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { MemoryFilterPills, type MemoryFilterType } from './MemoryFilterPills';
import { MemoryRecordCard } from './MemoryRecordCard';
import { MemoryInspector } from './MemoryInspector';
import { NewDecisionModal } from './NewDecisionModal';
import type { BMSRecord, Artifact } from '@/types';
import {
  BrainCircuit,
  Search,
  Plus,
  X,
  Layers,
  Check,
} from 'lucide-react';

export function MemoryExplorerPage() {
  const { activeProject } = useApp();
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<MemoryFilterType>('all');
  const [activeRecord, setActiveRecord] = useState<BMSRecord | null>(null);

  // New Decision Modal
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false);

  // Toast feedback state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const searchInputRef = useRef<HTMLInputElement>(null);

  const showToast = (msg: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(msg);
    toastTimeoutRef.current = setTimeout(() => setToastMessage(null), 3000);
  };

  // Keyboard shortcut '/' to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === '/' &&
        document.activeElement !== searchInputRef.current &&
        !['INPUT', 'TEXTAREA', 'SELECT'].includes((document.activeElement?.tagName || ''))
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch records and artifacts
  const loadData = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [recsRes, artsRes] = await Promise.allSettled([
        api.listRecords(activeProject.project_id),
        api.listArtifacts(activeProject.project_id),
      ]);

      const loadedRecords = recsRes.status === 'fulfilled' ? recsRes.value : [];
      const loadedArtifacts = artsRes.status === 'fulfilled' ? artsRes.value : [];

      setRecords(loadedRecords);
      setArtifacts(loadedArtifacts);
    } catch {
      setRecords([]);
      setArtifacts([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeProject?.project_id]);

  // Normalize artifacts into BMSRecords for unified search & filtering
  const unifiedItems: BMSRecord[] = useMemo(() => {
    const normalizedArtifacts: BMSRecord[] = artifacts.map((art) => ({
      record_id: art.artifact_id,
      schema_version: '0.1',
      record_type: 'artifact' as any,
      title: art.filename,
      summary: `${art.content_type || 'application/octet-stream'} • ${(art.byte_size / 1024).toFixed(1)} KB`,
      author: 'system',
      created_at: art.created_at,
      updated_at: art.created_at,
      project_id: art.project_id,
      verification_status: 'verified',
      tags: ['artifact', art.content_type?.split('/')[1] || 'binary'],
      attributes: art.metadata || {},
      content: `Artifact ID: ${art.artifact_id}\nFilename: ${art.filename}\nSHA256: ${art.sha256_hash}\nSize: ${art.byte_size} bytes`,
      revision: 1,
      _rawArtifact: art,
    } as BMSRecord & { _rawArtifact: Artifact }));

    return [...records, ...normalizedArtifacts];
  }, [records, artifacts]);

  // Calculate counts per filter pill
  const filterCounts = useMemo(() => {
    const counts: Record<MemoryFilterType, number> = {
      all: unifiedItems.length,
      task: 0,
      decision: 0,
      checkpoint: 0,
      knowledge: 0,
      agent: 0,
      artifact: 0,
    };

    unifiedItems.forEach((item) => {
      const type = (item.record_type as string).toLowerCase() as MemoryFilterType;
      if (counts[type] !== undefined) {
        counts[type]++;
      }
    });

    return counts;
  }, [unifiedItems]);

  // Filter records based on search query and active filter pill
  const filteredRecords = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return unifiedItems.filter((item) => {
      // Type filter
      if (activeFilter !== 'all' && (item.record_type as string).toLowerCase() !== activeFilter) {
        return false;
      }

      // Search filter
      if (!q) return true;
      const titleMatch = item.title?.toLowerCase().includes(q);
      const summaryMatch = item.summary?.toLowerCase().includes(q);
      const idMatch = item.record_id?.toLowerCase().includes(q);
      const contentMatch = item.content?.toLowerCase().includes(q);
      const tagMatch = item.tags?.some((t) => t.toLowerCase().includes(q));

      return Boolean(titleMatch || summaryMatch || idMatch || contentMatch || tagMatch);
    });
  }, [unifiedItems, searchQuery, activeFilter]);

  // Clear activeRecord if it gets filtered out by search or filter
  useEffect(() => {
    if (activeRecord && !filteredRecords.some((r) => r.record_id === activeRecord.record_id)) {
      setActiveRecord(null);
    }
  }, [filteredRecords, activeRecord]);

  const handleSelectRelated = (relatedId: string) => {
    const found = unifiedItems.find((r) => r.record_id === relatedId);
    if (found) {
      setActiveRecord(found);
      setActiveFilter('all');
    }
  };

  const handleNewDecisionSuccess = (created: BMSRecord) => {
    setRecords((prev) => [created, ...prev]);
    setActiveRecord(created);
    showToast(`Decision recorded: ${created.title}`);
  };

  if (!activeProject) {
    return (
      <EmptyState
        icon={<BrainCircuit className="h-10 w-10 text-muted-foreground" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to inspect the BMS memory graph."
      />
    );
  }

  return (
    <div className="flex flex-col space-y-4 animate-page-enter select-none pb-8 h-[calc(100vh-80px)]">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-8 z-50 px-4 py-2.5 rounded-xl bg-card/90 backdrop-blur-md border border-ice/40 shadow-[0_0_25px_rgba(56,189,248,0.3)] text-xs text-foreground font-semibold flex items-center space-x-2 animate-bounce">
          <Check className="h-4 w-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. Header & Controls: Title, Search Input, + New Decision */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3.5 rounded-2xl bg-card/60 backdrop-blur-md border border-ice/15 shadow-[0_4px_24px_rgba(0,0,0,0.25)] shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-ice/10 border border-ice/25 text-ice">
            <BrainCircuit className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-foreground tracking-tight flex items-center space-x-2">
              <span>Memory Explorer</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-ice/15 text-ice border border-ice/30 font-bold">
                BMS v0.1
              </span>
            </h1>
            <p className="text-xs text-muted-foreground">
              Search and inspect immutable memory records, ADR decisions, and artifacts.
            </p>
          </div>
        </div>

        {/* Right Action: + New Decision Button */}
        <div className="flex items-center space-x-2.5 self-end md:self-auto">
          <button
            onClick={() => setIsDecisionModalOpen(true)}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-chilli hover:bg-chilli/90 text-white font-bold text-xs shadow-[0_0_20px_rgba(239,68,68,0.35)] transition-all active:scale-[0.98]"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>+ New decision</span>
          </button>
        </div>
      </div>

      {/* 2. Large Search Input & Filter Pills */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 shrink-0">
        {/* Large Search Input with "/" shortcut hint */}
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search records by title, summary, content, or ID... (press '/' to focus)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-10 pl-10 pr-20 rounded-xl border border-ice/20 focus:border-ice/60 bg-card/60 backdrop-blur-md text-foreground placeholder:text-muted-foreground text-xs shadow-inner focus:outline-none focus:ring-1 focus:ring-ice/50 transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center space-x-1.5">
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="p-1 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                title="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/80 bg-secondary/60 text-muted-foreground shadow-xs">
              /
            </kbd>
          </div>
        </div>

        {/* Filter Pills with Sliding Indicator */}
        <div className="shrink-0">
          <MemoryFilterPills
            activeFilter={activeFilter}
            onChangeFilter={(f) => setActiveFilter(f)}
            counts={filterCounts}
          />
        </div>
      </div>

      {/* 3. Main Two-Column Layout (List + Inspector) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0 overflow-hidden">
        {/* Left Column: Result List (5 of 12 cols on desktop) */}
        <div className="lg:col-span-5 flex flex-col h-full rounded-2xl bg-card/40 backdrop-blur-md border border-ice/15 shadow-[0_8px_32px_rgba(0,0,0,0.2)] overflow-hidden">
          {/* List Header */}
          <div className="p-3 border-b border-ice/15 bg-card/60 flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-semibold text-foreground flex items-center space-x-1.5">
              <Layers className="h-3.5 w-3.5 text-ice" />
              <span>Matching Records</span>
            </span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-secondary/80 text-foreground font-semibold">
              {filteredRecords.length}
            </span>
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {isLoading && unifiedItems.length === 0 ? (
              <div className="py-20 flex justify-center">
                <LoadingSpinner text="Retrieving memory records and artifacts..." />
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="py-16 text-center text-muted-foreground px-4">
                <BrainCircuit className="h-10 w-10 mx-auto text-muted-foreground/30 mb-2" />
                <h4 className="text-sm font-semibold text-foreground">
                  No records match your search
                </h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                  Try adjusting your query, clearing filters, or record a new architectural decision.
                </p>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="mt-3 px-3 py-1 rounded-xl bg-ice/10 hover:bg-ice/20 border border-ice/30 text-ice text-xs font-semibold transition-colors"
                  >
                    Clear Search
                  </button>
                )}
              </div>
            ) : (
              filteredRecords.map((item) => (
                <MemoryRecordCard
                  key={item.record_id}
                  record={item}
                  isSelected={activeRecord?.record_id === item.record_id}
                  onClick={() => setActiveRecord(item)}
                />
              ))
            )}
          </div>
        </div>

        {/* Right Column: Inspector for Selected Record (7 of 12 cols on desktop) */}
        <div className="lg:col-span-7 flex flex-col h-full min-h-0">
          <MemoryInspector
            record={activeRecord}
            activeProject={activeProject}
            onSelectRelatedRecord={handleSelectRelated}
          />
        </div>
      </div>

      {/* New Decision Modal */}
      {isDecisionModalOpen && (
        <NewDecisionModal
          isOpen={isDecisionModalOpen}
          onClose={() => setIsDecisionModalOpen(false)}
          projectId={activeProject.project_id}
          onSuccess={handleNewDecisionSuccess}
        />
      )}
    </div>
  );
}
