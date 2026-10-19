import { useState, useEffect } from 'react';
import {
  Copy,
  Check,
  CheckCircle2,
  AlertCircle,
  FileCode,
  FileText,
  FileSpreadsheet,
  File,
  Download,
  Eye,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Layers,
  Network,
  Share2,
  Tag,
} from 'lucide-react';
import type { BMSRecord, Project } from '@/types';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Modal } from '@/components/ui/Modal';

interface MemoryInspectorProps {
  record: BMSRecord | null;
  activeProject: Project | null;
  onSelectRelatedRecord?: (recordId: string) => void;
}

export function MemoryInspector({
  record,
  activeProject,
  onSelectRelatedRecord,
}: MemoryInspectorProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'json' | 'related'>('overview');
  const [copied, setCopied] = useState(false);

  // Decision Accordion States
  const [isDecisionOpen, setIsDecisionOpen] = useState(true);
  const [isRationaleOpen, setIsRationaleOpen] = useState(true);
  const [isAlternativesOpen, setIsAlternativesOpen] = useState(true);
  const [isTasksOpen, setIsTasksOpen] = useState(true);

  // Raw Artifact Viewer Modal
  const [isRawModalOpen, setIsRawModalOpen] = useState(false);

  // Schema Validation State for JSON Tab
  const [validationResult, setValidationResult] = useState<{
    isValid: boolean;
    errors: string[];
    isChecked: boolean;
  }>({ isValid: true, errors: [], isChecked: false });
  const [isValidating, setIsValidating] = useState(false);

  // Related Graph Links State
  const [relatedNodes, setRelatedNodes] = useState<{ id: string; label: string; type: string }[]>([]);
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);

  // Validate on record change or when switching to JSON tab
  useEffect(() => {
    if (!record) return;

    let isMounted = true;
    setIsValidating(true);

    api
      .validateRecord(record)
      .then((res) => {
        if (!isMounted) return;
        setValidationResult({
          isValid: Boolean(res.valid ?? res.is_valid),
          errors: res.errors || [],
          isChecked: true,
        });
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        setValidationResult({
          isValid: false,
          errors: [err instanceof Error ? err.message : 'Validation failed'],
          isChecked: true,
        });
      })
      .finally(() => {
        if (isMounted) setIsValidating(false);
      });

    return () => {
      isMounted = false;
    };
  }, [record?.record_id]);

  // Load Related Graph Nodes on tab switch or record change
  useEffect(() => {
    if (!record || !activeProject) return;

    let isMounted = true;
    setIsLoadingRelated(true);

    api
      .getSubgraph(activeProject.project_id, record.record_id, 1)
      .then((subgraph) => {
        if (!isMounted) return;
        const related = (subgraph.nodes || [])
          .filter((n) => n.id !== record.record_id)
          .map((n) => ({
            id: n.id,
            label: String(n.label || n.properties?.title || n.id),
            type: n.type || 'Node',
          }));
        setRelatedNodes(related);
      })
      .catch(() => {
        if (isMounted) setRelatedNodes([]);
      })
      .finally(() => {
        if (isMounted) setIsLoadingRelated(false);
      });

    return () => {
      isMounted = false;
    };
  }, [record?.record_id, activeProject?.project_id]);

  if (!record) {
    return (
      <div className="h-full min-h-[450px] flex flex-col items-center justify-center p-8 rounded-2xl glass-card border border-border-subtle text-center text-text-muted select-none">
        <Layers className="h-10 w-10 text-text-muted/30 mb-3" />
        <h3 className="text-sm font-semibold text-text-primary">No Record Selected</h3>
        <p className="text-xs text-text-muted mt-1 max-w-sm">
          Select any task, decision, checkpoint, knowledge item, or artifact from the list to inspect its schema and metadata.
        </p>
      </div>
    );
  }

  const handleCopyJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(record, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const filename = (record as any)._rawArtifact?.filename || `${record.record_id}.json`;
    const content =
      (record as any)._rawArtifact
        ? record.content || JSON.stringify(record, null, 2)
        : JSON.stringify(record, null, 2);
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isDecision = record.record_type === 'decision';
  const isArtifact = record.record_type === ('artifact' as any) || Boolean((record as any)._rawArtifact);

  // Extract decision details
  const decisionStatement =
    record.attributes?.decision || (record as any).decision || record.summary || 'No statement provided.';
  const rationaleText =
    record.attributes?.rationale || (record as any).rationale || record.content || 'No rationale documented.';

  let alternativesList: string[] = [];
  if (Array.isArray(record.attributes?.alternatives)) {
    alternativesList = record.attributes.alternatives as string[];
  } else if (Array.isArray((record as any).alternatives)) {
    alternativesList = (record as any).alternatives;
  } else if (typeof record.attributes?.alternatives === 'string') {
    alternativesList = [record.attributes.alternatives];
  }

  let affectedTasksList: string[] = [];
  if (Array.isArray(record.attributes?.affected_tasks)) {
    affectedTasksList = record.attributes.affected_tasks as string[];
  } else if (Array.isArray((record as any).affected_tasks)) {
    affectedTasksList = (record as any).affected_tasks;
  } else if (Array.isArray(record.tags)) {
    affectedTasksList = record.tags.filter(
      (t) => t.toLowerCase().startsWith('task-') || t.toLowerCase().startsWith('task_')
    );
  }

  // Artifact file icon
  const getArtifactIcon = (filename = '') => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    if (['json', 'yaml', 'yml', 'ts', 'js', 'py', 'sh', 'sql'].includes(ext)) {
      return <FileCode className="h-6 w-6 text-steel-500" />;
    }
    if (['csv', 'tsv', 'xlsx'].includes(ext)) {
      return <FileSpreadsheet className="h-6 w-6 text-emerald-400" />;
    }
    if (['md', 'txt', 'log'].includes(ext)) {
      return <FileText className="h-6 w-6 text-steel-500" />;
    }
    return <File className="h-6 w-6 text-amber-400" />;
  };

  return (
    <div className="flex flex-col h-full rounded-2xl glass-card border border-border-subtle shadow-sm overflow-hidden select-none">
      {/* Header Strip */}
      <div className="p-4 border-b border-border-subtle bg-surface/50 dark:bg-white/[0.02] space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-lava-orange px-2 py-0.5 rounded-lg bg-lava-orange/10 border border-lava-orange/20">
              ID: {record.record_id}
            </span>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-text-primary font-semibold border border-border-subtle">
              {record.record_type}
            </span>
            <span className="text-[10px] font-mono text-text-muted">
              v{record.schema_version || '0.1'}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            {record.verification_status === 'verified' ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                <ShieldCheck className="h-3 w-3" />
                <span>verified</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30">
                <ShieldAlert className="h-3 w-3" />
                <span>{record.verification_status || 'unverified'}</span>
              </span>
            )}
          </div>
        </div>

        <div>
          <h2 className="text-base font-bold text-text-primary leading-snug">
            {record.title}
          </h2>
          <div className="flex items-center space-x-3 text-[11px] text-text-muted mt-1">
            <span>Author: <strong className="text-text-primary">{record.author}</strong></span>
            <span>•</span>
            <span className="flex items-center space-x-1">
              <Clock className="h-3 w-3 text-text-muted" />
              <span>{formatDate(record.created_at)}</span>
            </span>
          </div>
        </div>

        {/* Tab Navigation: Overview, JSON, Related */}
        <div className="flex items-center space-x-1 border-t border-border-subtle pt-3">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'overview'
                ? 'bg-ice-100 dark:bg-white/[0.08] text-text-primary border border-border-subtle font-bold shadow-xs'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Overview
          </button>

          <button
            onClick={() => setActiveTab('json')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1.5 ${
              activeTab === 'json'
                ? 'bg-ice-100 dark:bg-white/[0.08] text-text-primary border border-border-subtle font-bold shadow-xs'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <span>JSON</span>
            {validationResult.isChecked && (
              <span
                className={`h-2 w-2 rounded-full ${
                  validationResult.isValid ? 'bg-emerald-500' : 'bg-lava-red'
                }`}
              />
            )}
          </button>

          <button
            onClick={() => setActiveTab('related')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1.5 ${
              activeTab === 'related'
                ? 'bg-ice-100 dark:bg-white/[0.08] text-text-primary border border-border-subtle font-bold shadow-xs'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Network className="h-3 w-3" />
            <span>Related</span>
            {relatedNodes.length > 0 && (
              <span className="text-[10px] font-mono px-1.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-text-muted">
                {relatedNodes.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* ============================================================ */}
        {/* TAB 1: OVERVIEW */}
        {/* ============================================================ */}
        {activeTab === 'overview' && (
          <div className="space-y-4 animate-page-enter">
            {/* If Decision: Render Expandable Accordions */}
            {isDecision ? (
              <div className="space-y-3">
                {/* 1. Decision Accordion */}
                <div className="rounded-xl border border-ice/20 bg-background/50 overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsDecisionOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-foreground bg-ice/5 hover:bg-ice/10 transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-steel-500" />
                      <span>Decision Statement</span>
                    </span>
                    {isDecisionOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-text-muted" />
                    )}
                  </button>
                  {isDecisionOpen && (
                    <div className="p-3 text-xs text-text-primary leading-relaxed border-t border-border-subtle bg-surface/50 dark:bg-white/[0.02]">
                      {decisionStatement}
                    </div>
                  )}
                </div>

                {/* 2. Rationale Accordion */}
                <div className="rounded-xl border border-border-subtle bg-surface overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsRationaleOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-text-primary bg-ice-100/50 dark:bg-white/[0.02] hover:bg-ice-100 dark:hover:bg-white/[0.05] transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      <span>Rationale & Trade-Offs</span>
                    </span>
                    {isRationaleOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-text-muted" />
                    )}
                  </button>
                  {isRationaleOpen && (
                    <div className="p-3 text-xs text-text-primary whitespace-pre-wrap leading-relaxed border-t border-border-subtle bg-surface/50 dark:bg-white/[0.02]">
                      {rationaleText}
                    </div>
                  )}
                </div>

                {/* 3. Alternatives Accordion */}
                <div className="rounded-xl border border-border-subtle bg-surface overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsAlternativesOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-text-primary bg-ice-100/50 dark:bg-white/[0.02] hover:bg-ice-100 dark:hover:bg-white/[0.05] transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-amber-500" />
                      <span>Alternatives Considered</span>
                    </span>
                    {isAlternativesOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-text-muted" />
                    )}
                  </button>
                  {isAlternativesOpen && (
                    <div className="p-3 text-xs border-t border-border-subtle bg-surface/50 dark:bg-white/[0.02]">
                      {alternativesList.length === 0 ? (
                        <p className="text-text-muted italic">No alternatives recorded.</p>
                      ) : (
                        <ul className="space-y-1.5 list-disc list-inside text-text-primary">
                          {alternativesList.map((alt, idx) => (
                            <li key={idx} className="leading-relaxed">
                              {alt}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>

                {/* 4. Affected Tasks Accordion */}
                <div className="rounded-xl border border-border-subtle bg-surface overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsTasksOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-text-primary bg-ice-100/50 dark:bg-white/[0.02] hover:bg-ice-100 dark:hover:bg-white/[0.05] transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-lava-red" />
                      <span>Affected Tasks</span>
                    </span>
                    {isTasksOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-text-muted" />
                    )}
                  </button>
                  {isTasksOpen && (
                    <div className="p-3 text-xs border-t border-border-subtle bg-surface/50 dark:bg-white/[0.02]">
                      {affectedTasksList.length === 0 ? (
                        <p className="text-text-muted italic">No specific tasks linked.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {affectedTasksList.map((taskId) => (
                            <button
                              key={taskId}
                              onClick={() => onSelectRelatedRecord?.(taskId)}
                              className="px-2.5 py-1 rounded-lg bg-ice-100 dark:bg-white/[0.08] hover:bg-ice-200 border border-border-subtle text-text-primary font-mono font-semibold text-xs transition-colors shadow-sm"
                            >
                              {taskId}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : isArtifact ? (
              /* If Artifact: Render File Type, View Raw & Download Buttons */
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-surface border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2.5 rounded-xl bg-ice-100 dark:bg-white/[0.08] border border-border-subtle">
                      {getArtifactIcon(record.title)}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-text-primary">{record.title}</h4>
                      <p className="text-[11px] text-text-muted font-mono mt-0.5">
                        {record.summary || 'binary package artifact'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setIsRawModalOpen(true)}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-semibold transition-all shadow-sm"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      <span>View raw</span>
                    </button>

                    <button
                      onClick={handleDownload}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg btn-primary-lava text-xs font-semibold shadow-xs transition-all active:scale-[0.98]"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>Download</span>
                    </button>
                  </div>
                </div>

                {/* Artifact Metadata */}
                <div className="p-4 rounded-xl bg-surface border border-border-subtle space-y-2 text-xs">
                  <h5 className="font-semibold text-text-primary uppercase tracking-wider text-[10px]">
                    Artifact Specification
                  </h5>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2 rounded bg-ice-100 dark:bg-white/[0.06] border border-border-subtle">
                      <span className="text-[10px] text-text-muted block font-sans">Filename</span>
                      <span className="text-text-primary">{record.title}</span>
                    </div>
                    <div className="p-2 rounded bg-ice-100 dark:bg-white/[0.06] border border-border-subtle">
                      <span className="text-[10px] text-text-muted block font-sans">Identifier</span>
                      <span className="text-text-primary">{record.record_id}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* General Record Content */
              <div className="space-y-4">
                {record.summary && (
                  <div className="p-3.5 rounded-xl bg-ice-100/50 dark:bg-white/[0.03] border border-border-subtle">
                    <span className="text-[10px] uppercase font-bold text-text-muted block mb-1">
                      Summary
                    </span>
                    <p className="text-xs text-text-primary leading-relaxed">{record.summary}</p>
                  </div>
                )}

                {record.content && (
                  <div className="p-3.5 rounded-xl bg-surface border border-border-subtle">
                    <span className="text-[10px] uppercase font-bold text-steel-500 block mb-1">
                      Content Body
                    </span>
                    <p className="text-xs text-text-primary whitespace-pre-wrap leading-relaxed">
                      {record.content}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tags Strip */}
            {record.tags && record.tags.length > 0 && (
              <div className="p-3 rounded-xl bg-surface border border-border-subtle space-y-1.5">
                <span className="text-[10px] uppercase font-bold text-text-muted flex items-center space-x-1">
                  <Tag className="h-3 w-3" />
                  <span>Tags</span>
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {record.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-ice-100 dark:bg-white/[0.08] text-text-primary border border-border-subtle"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 2: JSON WITH SCHEMA VALIDATION BADGE */}
        {/* ============================================================ */}
        {activeTab === 'json' && (
          <div className="space-y-3 animate-page-enter">
            {/* Schema Validation Status Badge */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface border border-border-subtle">
              <div className="flex items-center space-x-2">
                {isValidating ? (
                  <span className="inline-flex items-center space-x-1.5 text-xs text-text-muted">
                    <span className="h-3 w-3 border-2 border-lava-orange border-t-transparent rounded-full animate-spin" />
                    <span>Validating against BMS schema...</span>
                  </span>
                ) : validationResult.isValid ? (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Schema Valid (BMS v0.1)</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-lava-red/10 text-lava-red border border-lava-red/20">
                    <AlertCircle className="h-3.5 w-3.5" />
                    <span>Schema Invalid ({validationResult.errors.length} errors)</span>
                  </span>
                )}
              </div>

              {/* Copy JSON Button */}
              <button
                onClick={handleCopyJSON}
                className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg btn-secondary-ice text-xs font-medium transition-all shadow-xs"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    <span className="text-emerald-500 font-bold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 text-text-muted" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
            </div>

            {/* Validation Error Callout if Invalid */}
            {!validationResult.isValid && validationResult.errors.length > 0 && (
              <div className="p-3 rounded-xl bg-lava-red/10 border border-lava-red/20 text-lava-red text-xs space-y-1">
                <span className="font-bold block">Validation Errors:</span>
                <ul className="list-disc list-inside space-y-0.5">
                  {validationResult.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Mono Code View */}
            <div className="relative rounded-xl border border-border-subtle bg-ice-100/50 dark:bg-bg-elevated p-3.5 overflow-x-auto shadow-xs">
              <pre className="font-mono text-[11px] text-text-primary leading-relaxed">
                {JSON.stringify(record, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 3: RELATED (GRAPH LINKS) */}
        {/* ============================================================ */}
        {activeTab === 'related' && (
          <div className="space-y-4 animate-page-enter">
            <div className="p-3.5 rounded-xl bg-ice-100/50 dark:bg-white/[0.02] border border-border-subtle">
              <div className="flex items-center space-x-2 text-xs font-semibold text-text-primary">
                <Network className="h-4 w-4 text-lava-orange" />
                <span>Knowledge Graph Topology Links</span>
              </div>
              <p className="text-[11px] text-text-muted mt-1">
                Connected memory entities, parent decisions, and implementing coordination tasks in FalkorDB.
              </p>
            </div>

            {isLoadingRelated ? (
              <div className="p-8 text-center text-xs text-text-muted">
                <span className="inline-block h-4 w-4 border-2 border-lava-orange border-t-transparent rounded-full animate-spin mb-2" />
                <p>Traversing graph relationships...</p>
              </div>
            ) : relatedNodes.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted bg-surface rounded-xl border border-border-subtle">
                <Share2 className="h-8 w-8 mx-auto text-text-muted/40 mb-2" />
                <p className="font-semibold text-text-primary">No direct graph connections</p>
                <p className="text-[11px] mt-0.5">
                  Run the FalkorDB re-rank or add task dependencies to link this node.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-bold text-text-muted block">
                  Connected Entities ({relatedNodes.length})
                </span>
                <div className="grid grid-cols-1 gap-2">
                  {relatedNodes.map((node) => (
                    <div
                      key={node.id}
                      onClick={() => onSelectRelatedRecord?.(node.id)}
                      className="p-3 rounded-xl bg-surface hover:bg-ice-100/50 dark:hover:bg-white/[0.04] border border-border-subtle hover:border-steel-500/50 flex items-center justify-between cursor-pointer transition-all shadow-xs"
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="p-1.5 rounded-lg bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border border-border-subtle font-mono text-[10px]">
                          {node.type}
                        </span>
                        <div>
                          <span className="text-xs font-bold text-text-primary block">
                            {node.label}
                          </span>
                          <span className="text-[10px] font-mono text-text-muted">
                            {node.id}
                          </span>
                        </div>
                      </div>

                      <ChevronRight className="h-3.5 w-3.5 text-text-muted" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Raw Artifact Modal */}
      {isRawModalOpen && (
        <Modal
          isOpen={isRawModalOpen}
          onClose={() => setIsRawModalOpen(false)}
          title={`Raw Content: ${record.title}`}
          description={`Viewing payload of artifact ${record.record_id}`}
        >
          <div className="space-y-3">
            <div className="max-h-[60vh] overflow-y-auto p-3.5 rounded-xl bg-background/90 border border-border font-mono text-xs text-ice-200">
              <pre>{record.content || JSON.stringify(record, null, 2)}</pre>
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 rounded-xl bg-ice text-background font-bold text-xs"
              >
                Download File
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
