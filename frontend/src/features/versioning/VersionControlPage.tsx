import { useEffect, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { formatDate, truncate } from '@/lib/utils';
import type { Branch, Commit, ConflictItem, Review, StructuredDiff } from '@/types';
import {
  GitBranch,
  GitCommit,
  GitMerge,
  AlertTriangle,
  MessageSquare,
  Plus,
  ShieldCheck,
} from 'lucide-react';

export function VersionControlPage() {
  const { activeProject } = useApp();
  const [commits, setCommits] = useState<Commit[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [activeTab, setActiveTab] = useState<'commits' | 'branches' | 'reviews' | 'conflicts'>('commits');
  const [selectedCommit, setSelectedCommit] = useState<Commit | null>(null);
  const [diff, setDiff] = useState<StructuredDiff | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Modals
  const [isBranchModalOpen, setIsBranchModalOpen] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');
  const [isMergeModalOpen, setIsMergeModalOpen] = useState(false);
  const [sourceBranch, setSourceBranch] = useState('');
  const [targetBranch, setTargetBranch] = useState('main');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadVCData = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [cmts, brs, revs, confs] = await Promise.allSettled([
        api.listCommits(activeProject.project_id),
        api.listBranches(activeProject.project_id),
        api.listReviews(activeProject.project_id),
        api.listConflicts(activeProject.project_id),
      ]);
      if (cmts.status === 'fulfilled') setCommits(cmts.value);
      if (brs.status === 'fulfilled') setBranches(brs.value);
      if (revs.status === 'fulfilled') setReviews(revs.value);
      if (confs.status === 'fulfilled') setConflicts(confs.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadVCData();
  }, [activeProject]);

  const handleSelectCommit = async (commit: Commit) => {
    setSelectedCommit(commit);
    if (!activeProject || commit.parent_hashes.length === 0) {
      setDiff(null);
      return;
    }
    try {
      const d = await api.getDiff(activeProject.project_id, commit.parent_hashes[0], commit.commit_hash);
      setDiff(d);
    } catch {
      setDiff(null);
    }
  };

  const handleCreateBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !newBranchName.trim()) return;
    setIsSubmitting(true);
    try {
      await api.createBranch(activeProject.project_id, { name: newBranchName.trim() });
      await loadVCData();
      setIsBranchModalOpen(false);
      setNewBranchName('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create branch');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMerge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !sourceBranch) return;
    setIsSubmitting(true);
    try {
      await api.mergeBranches(activeProject.project_id, {
        source_branch: sourceBranch,
        target_branch: targetBranch,
        author: { name: 'dashboard-user' },
      });
      await loadVCData();
      setIsMergeModalOpen(false);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Merge failed. Conflicts may exist.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!activeProject) {
    return (
      <EmptyState
        icon={<GitBranch className="h-10 w-10 text-muted-foreground" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to inspect version control history."
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Git-Style Version Control</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Immutable memory DAG, branches, diffs, and conflict resolution in "{activeProject.name}".
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={() => setIsBranchModalOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" />
            New Branch
          </Button>
          <Button size="sm" onClick={() => setIsMergeModalOpen(true)}>
            <GitMerge className="h-4 w-4 mr-1.5" />
            Merge Proposal
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab('commits')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'commits'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <GitCommit className="h-4 w-4" />
          <span>Commit History ({commits.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('branches')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'branches'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <GitBranch className="h-4 w-4" />
          <span>Branches ({branches.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('reviews')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'reviews'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          <span>Reviews ({reviews.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('conflicts')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'conflicts'
              ? 'border-destructive text-destructive font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Conflicts ({conflicts.length})</span>
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner text="Reading version control state..." />
      ) : activeTab === 'commits' ? (
        /* Commits & Diff Split View */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
            {commits.map((c) => {
              const isSelected = selectedCommit?.commit_hash === c.commit_hash;
              return (
                <div
                  key={c.commit_hash}
                  onClick={() => handleSelectCommit(c)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-primary bg-primary/10 shadow-sm'
                      : 'border-border bg-card hover:border-border/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-primary">
                      {truncate(c.commit_hash, 10)}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{formatDate(c.timestamp)}</span>
                  </div>
                  <h4 className="text-sm font-medium mt-1 text-foreground line-clamp-2">{c.message}</h4>
                  <div className="text-[11px] text-muted-foreground mt-2">Author: {c.author.name}</div>
                </div>
              );
            })}
          </div>

          <div className="lg:col-span-2">
            {selectedCommit ? (
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs font-mono text-muted-foreground">
                        Commit: {selectedCommit.commit_hash}
                      </span>
                      <CardTitle className="text-lg font-bold mt-1">{selectedCommit.message}</CardTitle>
                      <CardDescription className="text-xs mt-1">
                        Author: {selectedCommit.author.name} ({selectedCommit.author.email || 'local'}) •{' '}
                        {formatDate(selectedCommit.timestamp)}
                      </CardDescription>
                    </div>
                    {selectedCommit.parent_hashes.length > 0 && (
                      <Badge variant="outline" className="font-mono text-[10px]">
                        Parent: {truncate(selectedCommit.parent_hashes[0], 8)}
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="border-t border-border pt-3">
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                      Structured Diff Against Parent
                    </h5>
                    {diff && Object.keys(diff.changed_records).length > 0 ? (
                      <div className="space-y-3">
                        {Object.entries(diff.changed_records).map(([recId, change]) => (
                          <div key={recId} className="bg-muted/30 p-3 rounded border border-border text-xs">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="font-mono font-medium">{recId}</span>
                              <Badge variant="outline" className="text-[10px] uppercase">
                                {change.operation}
                              </Badge>
                            </div>
                            <div className="space-y-1 font-mono text-[11px]">
                              {Object.entries(change.fields).map(([fieldName, vals]) => (
                                <div key={fieldName} className="bg-card p-2 rounded border border-border">
                                  <span className="text-muted-foreground font-semibold">{fieldName}: </span>
                                  <div className="text-destructive line-through">
                                    - {JSON.stringify(vals.old)}
                                  </div>
                                  <div className="text-emerald-400 font-medium">
                                    + {JSON.stringify(vals.new)}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        No field changes detected or initial root commit.
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="h-full flex items-center justify-center p-12 text-center text-muted-foreground">
                <p className="text-sm">Select a commit to view full details and structured before/after diffs.</p>
              </Card>
            )}
          </div>
        </div>
      ) : activeTab === 'branches' ? (
        /* Branches View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {branches.map((b) => (
            <Card key={b.name} className="flex flex-col justify-between">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-semibold flex items-center">
                    <GitBranch className="h-4 w-4 mr-2 text-primary" />
                    {b.name}
                  </CardTitle>
                  {b.is_default && <Badge variant="default">Default</Badge>}
                </div>
                <CardDescription className="font-mono text-xs mt-1">
                  HEAD: {truncate(b.head_commit_hash, 12)}
                </CardDescription>
              </CardHeader>
              <CardFooter className="pt-2 border-t border-border flex justify-between">
                <span className="text-xs text-muted-foreground flex items-center">
                  <ShieldCheck className="h-3.5 w-3.5 mr-1 text-emerald-400" /> Protected
                </span>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : activeTab === 'reviews' ? (
        /* Reviews View */
        <div className="space-y-4">
          {reviews.length === 0 ? (
            <EmptyState
              icon={<MessageSquare className="h-8 w-8 text-muted-foreground" />}
              title="No Open Reviews"
              description="There are currently no open pull request or branch reviews for this project."
            />
          ) : (
            reviews.map((r) => (
              <Card key={r.review_id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold">{r.title}</CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {r.source_branch} → {r.target_branch} • Author: {r.author_id} • {formatDate(r.created_at)}
                      </CardDescription>
                    </div>
                    <Badge variant={r.status === 'approved' ? 'success' : 'secondary'} className="capitalize">
                      {r.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{r.description || 'No description provided.'}</p>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      ) : (
        /* Conflicts View */
        <div className="space-y-4">
          {conflicts.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground">
              <ShieldCheck className="h-10 w-10 mx-auto text-emerald-400 mb-2" />
              <h3 className="text-base font-semibold text-foreground">Clean State</h3>
              <p className="text-xs mt-1">No three-way merge conflicts detected across active branches.</p>
            </Card>
          ) : (
            conflicts.map((conf) => (
              <Card key={`${conf.record_id}-${conf.field_name}`} className="border-amber-500/40">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold text-amber-300">
                      Conflict in {conf.record_id} • Field: {conf.field_name}
                    </CardTitle>
                    <Badge variant="warning">{conf.is_resolved ? 'Resolved' : 'Pending Resolution'}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
                    <div className="p-3 bg-muted/40 rounded border border-border">
                      <span className="text-muted-foreground block font-sans font-semibold mb-1">Base Value</span>
                      <pre>{JSON.stringify(conf.base_value, null, 2)}</pre>
                    </div>
                    <div className="p-3 bg-primary/10 rounded border border-primary/20">
                      <span className="text-primary block font-sans font-semibold mb-1">Source (Branch)</span>
                      <pre>{JSON.stringify(conf.source_value, null, 2)}</pre>
                    </div>
                    <div className="p-3 bg-accent/40 rounded border border-accent">
                      <span className="text-accent-foreground block font-sans font-semibold mb-1">Target (Main)</span>
                      <pre>{JSON.stringify(conf.target_value, null, 2)}</pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* New Branch Modal */}
      <Modal
        isOpen={isBranchModalOpen}
        onClose={() => setIsBranchModalOpen(false)}
        title="Create Branch"
        description="Fork a separate branch to isolate AI agent memory updates."
      >
        <form onSubmit={handleCreateBranch} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Branch Name *</label>
            <Input
              placeholder="e.g. agent-feature-experiment"
              value={newBranchName}
              onChange={(e) => setNewBranchName(e.target.value)}
              required
            />
          </div>
          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsBranchModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create Branch
            </Button>
          </div>
        </form>
      </Modal>

      {/* Merge Proposal Modal */}
      <Modal
        isOpen={isMergeModalOpen}
        onClose={() => setIsMergeModalOpen(false)}
        title="Propose Branch Merge"
        description="Merge memory changes from a feature branch into the target branch."
      >
        <form onSubmit={handleMerge} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Source Branch *</label>
            <select
              value={sourceBranch}
              onChange={(e) => setSourceBranch(e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs"
              required
            >
              <option value="">Select source branch</option>
              {branches.map((b) => (
                <option key={b.name} value={b.name}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Target Branch *</label>
            <select
              value={targetBranch}
              onChange={(e) => setTargetBranch(e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs"
              required
            >
              {branches.map((b) => (
                <option key={b.name} value={b.name}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsMergeModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Execute Merge
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
