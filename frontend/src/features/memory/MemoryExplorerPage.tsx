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

  // Clear activeRecord if it gets filtered out by search or filter, or auto-select first record
  useEffect(() => {
    if (activeRecord && !filteredRecords.some((r) => r.record_id === activeRecord.record_id)) {
      setActiveRecord(filteredRecords.length > 0 ? filteredRecords[0] : null);
    } else if (!activeRecord && filteredRecords.length > 0) {
      setActiveRecord(filteredRecords[0]);
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
        <div className="fixed bottom-6 right-6 z-toast flex items-center space-x-3 px-4 py-3 rounded-lg solid-floating-surface border-l-4 !border-l-lava-orange text-text-primary text-xs font-medium animate-page-enter">
          <div className="h-5 w-5 rounded-full bg-lava-orange/15 border border-lava-orange/30 flex items-center justify-center text-lava-orange shrink-0">
            <Check className="h-3 w-3" />
          </div>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. Header & Controls: Title, Search Input, + New Decision */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3.5 glass-card shadow-sm shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-ice-100 dark:bg-white/[0.08] border border-border-subtle text-steel-700 dark:text-text-primary">
            <BrainCircuit className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-heading text-lg font-bold text-text-primary tracking-tight flex items-center space-x-2">
              <span>Memory</span>
              <span className="sr-only">Memory Explorer</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border border-border-subtle font-medium">
                BMS v0.2
              </span>
            </h1>
            <p className="text-xs text-text-muted mt-0.5">
              Everything your agents have saved about this project.
            </p>
          </div>
        </div>

        {/* Right Action: Add Memory */}
        <div className="flex items-center space-x-2.5 self-end md:self-auto">
          <button
            onClick={() => setIsDecisionModalOpen(true)}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg btn-primary-lava text-xs font-semibold shadow-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Memory</span>
          </button>
        </div>
      </div>

      {/* 2. Large Search Input & Filter Pills */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 shrink-0">
        {/* Large Search Input with "/" shortcut hint */}
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search records by title, summary, content, or ID... (press '/' to focus)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-10 pl-10 pr-20 rounded-xl border border-border-subtle focus:border-steel-500 bg-surface dark:bg-bg-elevated text-text-primary placeholder:text-text-muted text-xs shadow-xs focus:outline-none focus:ring-1 focus:ring-steel-500/50 transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center space-x-1.5">
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="p-1 rounded-lg hover:bg-ice-100 dark:hover:bg-white/[0.08] text-text-muted hover:text-text-primary transition-colors"
                title="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border-subtle bg-ice-100 dark:bg-white/[0.08] text-text-muted shadow-xs">
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
        <div className="lg:col-span-5 flex flex-col h-full rounded-2xl glass-card border border-border-subtle shadow-sm overflow-hidden">
          {/* List Header */}
          <div className="p-3 border-b border-border-subtle bg-surface/50 dark:bg-white/[0.02] flex items-center justify-between text-xs text-text-muted">
            <span className="font-semibold text-text-primary flex items-center space-x-1.5">
              <Layers className="h-3.5 w-3.5 text-lava-orange" />
              <span>Matching Records</span>
            </span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-text-primary font-semibold border border-border-subtle">
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
              <div className="py-16 text-center text-text-muted px-4">
                <BrainCircuit className="h-10 w-10 mx-auto text-text-muted/40 mb-2" />
                <h4 className="text-sm font-semibold text-text-primary">
                  {unifiedItems.length === 0 ? 'No memory records yet' : 'No records match your search'}
                </h4>
                <p className="text-xs text-text-muted mt-1 max-w-xs mx-auto">
                  {unifiedItems.length === 0
                    ? 'As your AI agents collaborate, architectural decisions and runbooks will appear here.'
                    : 'Try adjusting your query, clearing filters, or record a new architectural decision.'}
                </p>
                {searchQuery || activeFilter !== 'all' ? (
                  <button
                    onClick={() => {
                      setSearchQuery('');
                      setActiveFilter('all');
                    }}
                    className="mt-3 px-3 py-1 rounded-lg bg-ice-100 dark:bg-white/[0.08] hover:bg-ice-200 border border-border-subtle text-text-primary text-xs font-semibold transition-colors"
                  >
                    Reset Filters
                  </button>
                ) : (
                  <button
                    onClick={() => setIsDecisionModalOpen(true)}
                    className="mt-3 px-3 py-1.5 rounded-lg btn-primary-lava text-xs font-semibold transition-colors"
                  >
                    Add Decision
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
