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
      <div className="h-full min-h-[450px] flex flex-col items-center justify-center p-8 rounded-2xl bg-card/40 backdrop-blur-md border border-ice/15 text-center text-muted-foreground select-none">
        <Layers className="h-10 w-10 text-muted-foreground/30 mb-3 animate-pulse" />
        <h3 className="text-sm font-semibold text-foreground">No Record Selected</h3>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm">
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
      return <FileCode className="h-6 w-6 text-ice" />;
    }
    if (['csv', 'tsv', 'xlsx'].includes(ext)) {
      return <FileSpreadsheet className="h-6 w-6 text-emerald-400" />;
    }
    if (['md', 'txt', 'log'].includes(ext)) {
      return <FileText className="h-6 w-6 text-ice-200" />;
    }
    return <File className="h-6 w-6 text-amber-400" />;
  };

  return (
    <div className="flex flex-col h-full rounded-2xl bg-card/60 backdrop-blur-md border border-ice/20 shadow-[0_8px_32px_rgba(0,0,0,0.3)] overflow-hidden select-none">
      {/* Header Strip */}
      <div className="p-4 border-b border-ice/15 bg-card/80 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-ice px-2 py-0.5 rounded-lg bg-ice/10 border border-ice/20">
              ID: {record.record_id}
            </span>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-secondary text-foreground font-semibold border border-border">
              {record.record_type}
            </span>
            <span className="text-[10px] font-mono text-muted-foreground">
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
          <h2 className="text-base font-bold text-foreground leading-snug">
            {record.title}
          </h2>
          <div className="flex items-center space-x-3 text-[11px] text-muted-foreground mt-1">
            <span>Author: <strong className="text-foreground">{record.author}</strong></span>
            <span>•</span>
            <span className="flex items-center space-x-1">
              <Clock className="h-3 w-3 text-muted-foreground/70" />
              <span>{formatDate(record.created_at)}</span>
            </span>
          </div>
        </div>

        {/* Tab Navigation: Overview, JSON, Related */}
        <div className="flex items-center space-x-1 border-t border-border/40 pt-3">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1 rounded-xl text-xs font-semibold transition-colors ${
              activeTab === 'overview'
                ? 'bg-ice/20 text-ice border border-ice/35 font-bold shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Overview
          </button>

          <button
            onClick={() => setActiveTab('json')}
            className={`px-3 py-1 rounded-xl text-xs font-semibold transition-colors flex items-center space-x-1.5 ${
              activeTab === 'json'
                ? 'bg-ice/20 text-ice border border-ice/35 font-bold shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <span>JSON</span>
            {validationResult.isChecked && (
              <span
                className={`h-2 w-2 rounded-full ${
                  validationResult.isValid ? 'bg-emerald-400' : 'bg-chilli'
                }`}
              />
            )}
          </button>

          <button
            onClick={() => setActiveTab('related')}
            className={`px-3 py-1 rounded-xl text-xs font-semibold transition-colors flex items-center space-x-1.5 ${
              activeTab === 'related'
                ? 'bg-ice/20 text-ice border border-ice/35 font-bold shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Network className="h-3 w-3" />
            <span>Related</span>
            {relatedNodes.length > 0 && (
              <span className="text-[10px] font-mono px-1.5 rounded-full bg-secondary text-muted-foreground">
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
                      <span className="h-2 w-2 rounded-full bg-ice" />
                      <span>Decision Statement</span>
                    </span>
                    {isDecisionOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                  {isDecisionOpen && (
                    <div className="p-3 text-xs text-foreground/90 leading-relaxed border-t border-border/40 bg-card/40">
                      {decisionStatement}
                    </div>
                  )}
                </div>

                {/* 2. Rationale Accordion */}
                <div className="rounded-xl border border-ice/20 bg-background/50 overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsRationaleOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-foreground bg-ice/5 hover:bg-ice/10 transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-teal-400" />
                      <span>Rationale & Trade-Offs</span>
                    </span>
                    {isRationaleOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                  {isRationaleOpen && (
                    <div className="p-3 text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed border-t border-border/40 bg-card/40">
                      {rationaleText}
                    </div>
                  )}
                </div>

                {/* 3. Alternatives Accordion */}
                <div className="rounded-xl border border-ice/20 bg-background/50 overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsAlternativesOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-foreground bg-ice/5 hover:bg-ice/10 transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-amber-400" />
                      <span>Alternatives Considered</span>
                    </span>
                    {isAlternativesOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                  {isAlternativesOpen && (
                    <div className="p-3 text-xs border-t border-border/40 bg-card/40">
                      {alternativesList.length === 0 ? (
                        <p className="text-muted-foreground italic">No alternatives recorded.</p>
                      ) : (
                        <ul className="space-y-1.5 list-disc list-inside text-foreground/90">
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
                <div className="rounded-xl border border-ice/20 bg-background/50 overflow-hidden shadow-sm">
                  <button
                    onClick={() => setIsTasksOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between p-3 text-left font-semibold text-xs text-foreground bg-ice/5 hover:bg-ice/10 transition-colors"
                  >
                    <span className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-chilli" />
                      <span>Affected Tasks</span>
                    </span>
                    {isTasksOpen ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                  {isTasksOpen && (
                    <div className="p-3 text-xs border-t border-border/40 bg-card/40">
                      {affectedTasksList.length === 0 ? (
                        <p className="text-muted-foreground italic">No specific tasks linked.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {affectedTasksList.map((taskId) => (
                            <button
                              key={taskId}
                              onClick={() => onSelectRelatedRecord?.(taskId)}
                              className="px-2.5 py-1 rounded-lg bg-ice/10 hover:bg-ice/20 border border-ice/30 text-ice font-mono font-semibold text-xs transition-colors shadow-sm"
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
                <div className="p-4 rounded-xl bg-background/60 border border-ice/20 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2.5 rounded-xl bg-secondary/80 border border-border">
                      {getArtifactIcon(record.title)}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-foreground">{record.title}</h4>
                      <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                        {record.summary || 'binary package artifact'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setIsRawModalOpen(true)}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-ice/30 hover:border-ice/50 bg-ice/10 hover:bg-ice/20 text-ice text-xs font-semibold transition-all shadow-sm"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      <span>View raw</span>
                    </button>

                    <button
                      onClick={handleDownload}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-[0_0_15px_rgba(56,189,248,0.35)] transition-all active:scale-[0.98]"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>Download</span>
                    </button>
                  </div>
                </div>

                {/* Artifact Metadata */}
                <div className="p-4 rounded-xl bg-card/60 border border-border/80 space-y-2 text-xs">
                  <h5 className="font-semibold text-foreground uppercase tracking-wider text-[10px]">
                    Artifact Specification
                  </h5>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2 rounded bg-secondary/40">
                      <span className="text-[10px] text-muted-foreground block font-sans">Filename</span>
                      <span className="text-foreground">{record.title}</span>
                    </div>
                    <div className="p-2 rounded bg-secondary/40">
                      <span className="text-[10px] text-muted-foreground block font-sans">Identifier</span>
                      <span className="text-foreground">{record.record_id}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* General Record Content */
              <div className="space-y-4">
                {record.summary && (
                  <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/60">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
                      Summary
                    </span>
                    <p className="text-xs text-foreground leading-relaxed">{record.summary}</p>
                  </div>
                )}

                {record.content && (
                  <div className="p-3.5 rounded-xl bg-background/60 border border-ice/15">
                    <span className="text-[10px] uppercase font-bold text-ice block mb-1">
                      Content Body
                    </span>
                    <p className="text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed">
                      {record.content}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tags Strip */}
            {record.tags && record.tags.length > 0 && (
              <div className="p-3 rounded-xl bg-card/50 border border-border/60 space-y-1.5">
                <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center space-x-1">
                  <Tag className="h-3 w-3" />
                  <span>Tags</span>
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {record.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-secondary text-foreground border border-border"
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
            <div className="flex items-center justify-between p-3 rounded-xl bg-background/70 border border-border">
              <div className="flex items-center space-x-2">
                {isValidating ? (
                  <span className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground">
                    <span className="h-3 w-3 border-2 border-ice border-t-transparent rounded-full animate-spin" />
                    <span>Validating against BMS schema...</span>
                  </span>
                ) : validationResult.isValid ? (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-ice/15 text-ice border border-ice/35 shadow-[0_0_12px_rgba(56,189,248,0.25)]">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Schema Valid (BMS v0.1)</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-chilli/15 text-chilli border border-chilli/35 shadow-[0_0_12px_rgba(239,68,68,0.25)]">
                    <AlertCircle className="h-3.5 w-3.5" />
                    <span>Schema Invalid ({validationResult.errors.length} errors)</span>
                  </span>
                )}
              </div>

              {/* Copy JSON Button */}
              <button
                onClick={handleCopyJSON}
                className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-secondary/80 hover:bg-secondary border border-border text-xs font-medium text-foreground transition-all shadow-sm"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400 font-bold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
            </div>

            {/* Validation Error Callout if Invalid */}
            {!validationResult.isValid && validationResult.errors.length > 0 && (
              <div className="p-3 rounded-xl bg-chilli/10 border border-chilli/30 text-chilli text-xs space-y-1">
                <span className="font-bold block">Validation Errors:</span>
                <ul className="list-disc list-inside space-y-0.5">
                  {validationResult.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Mono Code View */}
            <div className="relative rounded-xl border border-ice/20 bg-background/90 p-3.5 overflow-x-auto shadow-inner">
              <pre className="font-mono text-[11px] text-ice-200 leading-relaxed">
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
            <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/60">
              <div className="flex items-center space-x-2 text-xs font-semibold text-foreground">
                <Network className="h-4 w-4 text-ice" />
                <span>Knowledge Graph Topology Links</span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Connected memory entities, parent decisions, and implementing coordination tasks in FalkorDB.
              </p>
            </div>

            {isLoadingRelated ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <span className="inline-block h-4 w-4 border-2 border-ice border-t-transparent rounded-full animate-spin mb-2" />
                <p>Traversing graph relationships...</p>
              </div>
            ) : relatedNodes.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground bg-card/40 rounded-xl border border-border">
                <Share2 className="h-8 w-8 mx-auto text-muted-foreground/40 mb-2" />
                <p className="font-semibold text-foreground">No direct graph connections</p>
                <p className="text-[11px] mt-0.5">
                  Run the FalkorDB re-rank or add task dependencies to link this node.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                  Connected Entities ({relatedNodes.length})
                </span>
                <div className="grid grid-cols-1 gap-2">
                  {relatedNodes.map((node) => (
                    <div
                      key={node.id}
                      onClick={() => onSelectRelatedRecord?.(node.id)}
                      className="p-3 rounded-xl bg-card/60 hover:bg-card border border-ice/20 hover:border-ice/40 flex items-center justify-between cursor-pointer transition-all shadow-sm"
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="p-1.5 rounded-lg bg-ice/10 text-ice border border-ice/20 font-mono text-[10px]">
                          {node.type}
                        </span>
                        <div>
                          <span className="text-xs font-bold text-foreground block">
                            {node.label}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {node.id}
                          </span>
                        </div>
                      </div>

                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
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
