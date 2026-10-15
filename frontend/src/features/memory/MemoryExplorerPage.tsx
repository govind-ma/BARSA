import React, { useEffect, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/utils';
import type { BMSRecord, RecordType, VerificationStatus } from '@/types';
import {
  BrainCircuit,
  Search,
  Plus,
  Filter,
  CheckCircle2,
  HelpCircle,
  XCircle,
  FileText,
} from 'lucide-react';

const recordTypes: RecordType[] = [
  'task',
  'requirement',
  'decision',
  'context',
  'constraint',
  'knowledge',
  'checkpoint',
  'agent',
];

export function MemoryExplorerPage() {
  const { activeProject } = useApp();
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [activeRecord, setActiveRecord] = useState<BMSRecord | null>(null);

  // New Record state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newSummary, setNewSummary] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState<RecordType>('knowledge');
  const [newStatus, setNewStatus] = useState<VerificationStatus>('verified');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const loadRecords = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const typeFilter = selectedType === 'all' ? undefined : selectedType;
      const list = await api.listRecords(activeProject.project_id, typeFilter);
      setRecords(list);
    } catch {
      setRecords([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [activeProject, selectedType]);

  const filteredRecords = records.filter((r) => {
    const matchesSearch =
      r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.record_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = selectedStatus === 'all' || r.verification_status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject) return;
    setIsSubmitting(true);
    setValidationError(null);

    const candidateRecord = {
      record_id: `rec_${Date.now()}`,
      schema_version: '0.1.0',
      record_type: newType,
      title: newTitle.trim(),
      summary: newSummary.trim(),
      content: newContent.trim(),
      author: 'dashboard-user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      project_id: activeProject.project_id,
      verification_status: newStatus,
      tags: ['dashboard'],
      attributes: {},
      revision: 1,
    };

    try {
      // 1. Validate against BMS standard schema
      const val = await api.validateRecord(candidateRecord);
      if (!val.is_valid) {
        setValidationError(`BMS Validation Failed: ${val.errors.join(', ')}`);
        setIsSubmitting(false);
        return;
      }

      // 2. Persist
      await api.createRecord(activeProject.project_id, candidateRecord);
      await loadRecords();
      setIsCreateOpen(false);
      setNewTitle('');
      setNewSummary('');
      setNewContent('');
    } catch (err: unknown) {
      setValidationError(err instanceof Error ? err.message : 'Failed to save record');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!activeProject) {
    return (
      <EmptyState
        icon={<BrainCircuit className="h-10 w-10 text-muted-foreground" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to explore BMS memory records."
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Memory Explorer</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Explore structured BMS memory in project "{activeProject.name}".
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          Create Record
        </Button>
      </div>

      {/* Filter and Search Bar with Category Pills */}
      <div className="space-y-3 bg-card p-4 rounded-xl border border-border/80 shadow-xs">
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search records by title, summary, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9 text-xs rounded-lg"
            />
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="h-9 rounded-lg border border-input bg-card px-3 text-xs focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="verified">Verified</option>
              <option value="unverified">Unverified</option>
              <option value="inconclusive">Inconclusive</option>
              <option value="refuted">Refuted</option>
            </select>
          </div>
        </div>

        {/* Quick Category Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pt-1 pb-0.5">
          {['all', ...recordTypes].map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`px-3 py-1 rounded-full text-[11px] font-medium capitalize transition-all whitespace-nowrap ${
                selectedType === type
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/60'
              }`}
            >
              {type === 'all' ? 'All Types' : type}
            </button>
          ))}
        </div>
      </div>

      {/* Content: List + Detail Split View */}
      {isLoading ? (
        <LoadingSpinner text="Querying memory records..." />
      ) : filteredRecords.length === 0 ? (
        <EmptyState
          icon={<BrainCircuit className="h-10 w-10 text-muted-foreground" />}
          title="No Memory Records Found"
          description={
            records.length === 0
              ? 'This project does not have any BMS memory records yet.'
              : 'No records match your search or filter query.'
          }
          actionLabel="Add Memory Record"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Records List Column */}
          <div className="lg:col-span-1 space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {filteredRecords.map((r) => {
              const isSelected = activeRecord?.record_id === r.record_id;
              return (
                <div
                  key={r.record_id}
                  onClick={() => setActiveRecord(r)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-primary bg-primary/10 shadow-sm'
                      : 'border-border bg-card hover:border-border/80'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-mono text-muted-foreground">{r.record_id}</span>
                    <Badge variant="outline" className="text-[10px] capitalize">
                      {r.record_type}
                    </Badge>
                  </div>
                  <h4 className="text-sm font-semibold text-foreground line-clamp-1">{r.title}</h4>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{r.summary}</p>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50 text-[10px] text-muted-foreground">
                    <span className="flex items-center">
                      {r.verification_status === 'verified' ? (
                        <CheckCircle2 className="h-3 w-3 text-emerald-400 mr-1" />
                      ) : r.verification_status === 'refuted' ? (
                        <XCircle className="h-3 w-3 text-destructive mr-1" />
                      ) : (
                        <HelpCircle className="h-3 w-3 text-amber-400 mr-1" />
                      )}
                      {r.verification_status}
                    </span>
                    <span>Rev {r.revision}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Record Detail Column */}
          <div className="lg:col-span-2">
            {activeRecord ? (
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <Badge variant="default" className="capitalize text-xs">
                          {activeRecord.record_type}
                        </Badge>
                        <Badge
                          variant={
                            activeRecord.verification_status === 'verified'
                              ? 'success'
                              : activeRecord.verification_status === 'refuted'
                              ? 'destructive'
                              : 'warning'
                          }
                          className="capitalize text-xs"
                        >
                          {activeRecord.verification_status}
                        </Badge>
                      </div>
                      <CardTitle className="text-xl font-bold mt-2">{activeRecord.title}</CardTitle>
                      <CardDescription className="font-mono text-xs mt-1">
                        ID: {activeRecord.record_id} • Author: {activeRecord.author} • Updated:{' '}
                        {formatDate(activeRecord.updated_at)}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                      Summary
                    </h5>
                    <p className="text-sm text-foreground bg-muted/30 p-3 rounded border border-border">
                      {activeRecord.summary}
                    </p>
                  </div>

                  <div>
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                      Content Payload
                    </h5>
                    <pre className="p-3 bg-muted/50 rounded border border-border text-xs font-mono whitespace-pre-wrap max-h-72 overflow-y-auto">
                      {activeRecord.content || '(No content payload)'}
                    </pre>
                  </div>

                  {activeRecord.tags && activeRecord.tags.length > 0 && (
                    <div>
                      <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                        Tags
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeRecord.tags.map((tag) => (
                          <span
                            key={tag}
                            className="bg-accent text-accent-foreground px-2 py-0.5 rounded text-[11px] font-mono"
                          >
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="h-full flex items-center justify-center p-12 text-center text-muted-foreground">
                <div>
                  <FileText className="h-10 w-10 mx-auto text-muted-foreground/60 mb-2" />
                  <p className="text-sm">Select a memory record on the left to inspect its complete BMS specification.</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Create BMS Record Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create BMS Memory Record"
        description="Standardized AI memory record with schema validation."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {validationError && (
            <div className="p-3 text-xs bg-destructive/10 text-destructive border border-destructive/20 rounded">
              {validationError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Record Type *</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as RecordType)}
                className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs"
              >
                {recordTypes.map((t) => (
                  <option key={t} value={t} className="capitalize">
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Verification Status *</label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value as VerificationStatus)}
                className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs"
              >
                <option value="verified">Verified</option>
                <option value="unverified">Unverified</option>
                <option value="inconclusive">Inconclusive</option>
                <option value="refuted">Refuted</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Title *</label>
            <Input
              placeholder="e.g. SQLite Storage Architecture Decision"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Summary *</label>
            <Input
              placeholder="Concise 1-sentence summary"
              value={newSummary}
              onChange={(e) => setNewSummary(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Content (Markdown / Details)</label>
            <Textarea
              rows={4}
              placeholder="Structured details, reasoning, or constraints"
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
            />
          </div>

          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Validate & Save
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
