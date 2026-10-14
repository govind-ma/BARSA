import React, { useEffect, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  HardDrive,
  Download,
  Upload,
  ShieldCheck,
  FileCheck,
  Cloud,
  RefreshCw,
  ArrowUpRight,
  ArrowDownLeft,
  Trash2,
  FolderGit2,
  AlertTriangle,
  Plus,
} from 'lucide-react';
import type { RemoteResponse, SyncStatusReport } from '@/types';

export function StoragePage() {
  const { activeWorkspace, activeProject, systemInfo, refreshProjects } = useApp();
  const [importJson, setImportJson] = useState('');
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  // BYOS Sync State
  const [remotes, setRemotes] = useState<RemoteResponse[]>([]);
  const [syncStatuses, setSyncStatuses] = useState<Record<string, SyncStatusReport>>({});
  const [loadingRemotes, setLoadingRemotes] = useState(false);
  const [isAddRemoteOpen, setIsAddRemoteOpen] = useState(false);
  const [syncActionLoading, setSyncActionLoading] = useState<string | null>(null);
  const [syncFeedback, setSyncFeedback] = useState<{ id: string; type: 'success' | 'error'; message: string } | null>(null);

  // New Remote Form
  const [remoteName, setRemoteName] = useState('');
  const [providerType, setProviderType] = useState<'local' | 's3'>('local');
  const [localPath, setLocalPath] = useState('');
  const [s3Bucket, setS3Bucket] = useState('');
  const [s3Endpoint, setS3Endpoint] = useState('');
  const [s3Region, setS3Region] = useState('us-east-1');
  const [s3AccessKey, setS3AccessKey] = useState('');
  const [s3SecretKey, setS3SecretKey] = useState('');
  const [encryptionEnabled, setEncryptionEnabled] = useState(false);

  useEffect(() => {
    if (activeProject) {
      loadRemotes(activeProject.project_id);
    } else {
      setRemotes([]);
      setSyncStatuses({});
    }
  }, [activeProject]);

  const loadRemotes = async (projectId: string) => {
    setLoadingRemotes(true);
    try {
      const data = await api.listRemotes(projectId);
      setRemotes(data);
      // Fetch status for each remote
      for (const r of data) {
        checkStatus(r.id);
      }
    } catch {
      // Ignore initial error if sync endpoints not yet configured
    } finally {
      setLoadingRemotes(false);
    }
  };

  const checkStatus = async (remoteId: string) => {
    try {
      const st = await api.getRemoteStatus(remoteId);
      setSyncStatuses((prev) => ({ ...prev, [remoteId]: st }));
    } catch {
      // Ignored
    }
  };

  const handlePush = async (remoteId: string) => {
    setSyncActionLoading(`push-${remoteId}`);
    setSyncFeedback(null);
    try {
      const res = await api.pushRemote(remoteId);
      setSyncFeedback({
        id: remoteId,
        type: res.diverged ? 'error' : 'success',
        message: res.diverged
          ? 'Remote has diverged! Merge remote changes first.'
          : `Pushed successfully (${res.objects_uploaded} objects, ${res.bytes_transferred} bytes in ${res.duration_ms}ms)`,
      });
      await checkStatus(remoteId);
    } catch (err: unknown) {
      setSyncFeedback({
        id: remoteId,
        type: 'error',
        message: err instanceof Error ? err.message : 'Push failed',
      });
    } finally {
      setSyncActionLoading(null);
    }
  };

  const handlePull = async (remoteId: string) => {
    setSyncActionLoading(`pull-${remoteId}`);
    setSyncFeedback(null);
    try {
      const res = await api.pullRemote(remoteId);
      setSyncFeedback({
        id: remoteId,
        type: res.diverged ? 'error' : 'success',
        message: res.diverged
          ? 'Remote has diverged! A merge commit is required.'
          : `Pulled successfully (${res.objects_downloaded} objects in ${res.duration_ms}ms)`,
      });
      await checkStatus(remoteId);
    } catch (err: unknown) {
      setSyncFeedback({
        id: remoteId,
        type: 'error',
        message: err instanceof Error ? err.message : 'Pull failed',
      });
    } finally {
      setSyncActionLoading(null);
    }
  };

  const handleDeleteRemote = async (remoteId: string) => {
    if (!confirm('Are you sure you want to remove this remote configuration?')) return;
    try {
      await api.deleteRemote(remoteId);
      setRemotes((prev) => prev.filter((r) => r.id !== remoteId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete remote');
    }
  };

  const handleCreateRemote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !remoteName.trim()) return;

    try {
      const payload: Record<string, unknown> = {
        name: remoteName.trim(),
        provider_type: providerType,
        encryption_enabled: encryptionEnabled,
      };
      if (providerType === 'local') {
        payload.local_path = localPath.trim();
      } else {
        payload.s3_bucket_name = s3Bucket.trim();
        payload.s3_endpoint_url = s3Endpoint.trim() || undefined;
        payload.s3_region = s3Region.trim() || 'us-east-1';
        if (s3AccessKey && s3SecretKey) {
          payload.s3_access_key = s3AccessKey.trim();
          payload.s3_secret_key = s3SecretKey.trim();
        }
      }

      await api.createRemote(activeProject.project_id, payload);
      setIsAddRemoteOpen(false);
      // Reset form
      setRemoteName('');
      setLocalPath('');
      setS3Bucket('');
      setS3Endpoint('');
      setS3AccessKey('');
      setS3SecretKey('');
      await loadRemotes(activeProject.project_id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to configure remote');
    }
  };

  const handleExport = async () => {
    if (!activeProject) return;
    setIsExporting(true);
    try {
      const data = await api.exportProject(activeProject.project_id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `barsa-export-${activeProject.project_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setImportJson(event.target?.result as string);
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    if (!activeWorkspace || !importJson.trim()) return;
    setIsImporting(true);
    setImportStatus(null);
    try {
      const parsed = JSON.parse(importJson);
      const res = await api.importPackage(activeWorkspace.workspace_id, parsed);
      setImportStatus(`Success! Imported project with ID: ${res.project_id}`);
      await refreshProjects();
      setTimeout(() => {
        setIsImportOpen(false);
        setImportJson('');
        setImportStatus(null);
      }, 1500);
    } catch (err: unknown) {
      setImportStatus(err instanceof Error ? err.message : 'Failed to import package');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Storage & Cloud Synchronization (BYOS)</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Local-first storage engine, content-addressed storage (CAS), and user-owned remote synchronization.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {activeProject && (
            <Button size="sm" onClick={() => setIsAddRemoteOpen(true)}>
              <Plus className="h-4 w-4 mr-1.5" />
              Add Remote
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setIsImportOpen(true)}>
            <Upload className="h-4 w-4 mr-1.5" />
            Import BMS Package
          </Button>
          {activeProject && (
            <Button variant="outline" size="sm" onClick={handleExport} isLoading={isExporting}>
              <Download className="h-4 w-4 mr-1.5" />
              Export Project Memory
            </Button>
          )}
        </div>
      </div>

      {/* Storage Information Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center">
              <HardDrive className="h-4 w-4 mr-2 text-primary" />
              Storage Architecture
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Engine:</span>
              <span className="font-mono font-medium">{systemInfo?.storage_provider || 'SQLite'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">CAS Addressing:</span>
              <span className="font-medium text-foreground">SHA-256 Content-Addressed</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Encryption:</span>
              <span>AES-256-GCM (Optional)</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center">
              <ShieldCheck className="h-4 w-4 mr-2 text-emerald-400" />
              Data Integrity & Backups
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Local State:</span>
              <Badge variant="success" className="text-[10px]">
                Healthy (ACID WAL)
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Git Commit DAG:</span>
              <span>Authoritative Head</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Concurrency:</span>
              <span>Optimistic ETag Guards</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center">
              <FileCheck className="h-4 w-4 mr-2 text-sky-400" />
              BMS Portable Package Standard
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Standard Version:</span>
              <span className="font-mono font-medium">BMS v0.1</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Portability:</span>
              <span>JSON Container</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Supported BYOS:</span>
              <span>Local FS, S3, MinIO, R2</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cloud Synchronization Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight flex items-center">
              <Cloud className="h-5 w-5 mr-2 text-primary" />
              Configured Remote Repositories
            </h2>
            <p className="text-xs text-muted-foreground">
              User-owned storage destinations for incremental synchronization across devices.
            </p>
          </div>
          {activeProject && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadRemotes(activeProject.project_id)}
              disabled={loadingRemotes}
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loadingRemotes ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          )}
        </div>

        {!activeProject ? (
          <EmptyState
            title="No Project Selected"
            description="Select an active project from the navigation bar to manage remote storage and sync."
            icon={<FolderGit2 className="h-8 w-8 text-muted-foreground" />}
          />
        ) : remotes.length === 0 ? (
          <EmptyState
            title="No Remotes Configured"
            description="Add a Local Filesystem directory or S3 bucket to synchronize your project memory across devices."
            icon={<Cloud className="h-8 w-8 text-muted-foreground" />}
            action={
              <Button size="sm" onClick={() => setIsAddRemoteOpen(true)}>
                <Plus className="h-4 w-4 mr-1.5" />
                Configure Remote Storage
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {remotes.map((rem) => {
              const status = syncStatuses[rem.id];
              const isSyncing = syncActionLoading?.includes(rem.id);
              const feedback = syncFeedback?.id === rem.id ? syncFeedback : null;

              return (
                <Card key={rem.id} className="border border-border">
                  <CardContent className="p-4 sm:p-5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-sm">{rem.name}</span>
                          <Badge variant="outline" className="text-[10px] uppercase font-mono">
                            {rem.provider_type}
                          </Badge>
                          {rem.encryption_enabled && (
                            <Badge variant="secondary" className="text-[10px]">
                              AES-256 Encrypted
                            </Badge>
                          )}
                          {status && (
                            <Badge
                              variant={
                                status.status === 'up_to_date'
                                  ? 'success'
                                  : status.status === 'diverged'
                                  ? 'destructive'
                                  : 'warning'
                              }
                              className="text-[10px] capitalize font-mono"
                            >
                              {status.status.replace('_', ' ')}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground font-mono">
                          {rem.provider_type === 'local'
                            ? rem.local_path
                            : `s3://${rem.s3_bucket_name}/${rem.s3_prefix || ''}`}
                        </p>
                        {status && (
                          <div className="flex items-center space-x-4 text-[11px] text-muted-foreground pt-1">
                            <span>
                              Local HEAD: <strong className="font-mono text-foreground">{status.local_head_commit_id.slice(0, 8)}</strong>
                            </span>
                            {status.remote_head_commit_id && (
                              <span>
                                Remote HEAD: <strong className="font-mono text-foreground">{status.remote_head_commit_id.slice(0, 8)}</strong>
                              </span>
                            )}
                            {status.ahead_count > 0 && <span>Ahead: {status.ahead_count}</span>}
                            {status.behind_count > 0 && <span>Behind: {status.behind_count}</span>}
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePull(rem.id)}
                          isLoading={syncActionLoading === `pull-${rem.id}`}
                          disabled={isSyncing}
                        >
                          <ArrowDownLeft className="h-4 w-4 mr-1 text-sky-400" />
                          Pull
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handlePush(rem.id)}
                          isLoading={syncActionLoading === `push-${rem.id}`}
                          disabled={isSyncing}
                        >
                          <ArrowUpRight className="h-4 w-4 mr-1 text-primary" />
                          Push
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteRemote(rem.id)}
                          disabled={isSyncing}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Feedback alert */}
                    {feedback && (
                      <div
                        className={`mt-3 p-2.5 text-xs rounded border ${
                          feedback.type === 'success'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-destructive/10 text-destructive border-destructive/20'
                        }`}
                      >
                        {feedback.message}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Remote Modal */}
      <Modal
        isOpen={isAddRemoteOpen}
        onClose={() => setIsAddRemoteOpen(false)}
        title="Configure BYOS Remote Storage"
        description="Add a destination storage repository for content-addressed cloud synchronization."
      >
        <form onSubmit={handleCreateRemote} className="space-y-4">
          <Input
            label="Remote Name"
            placeholder="e.g., origin, s3-backup, local-share"
            value={remoteName}
            onChange={(e) => setRemoteName(e.target.value)}
            required
          />

          <div>
            <label className="block text-xs font-medium mb-1">Storage Provider Type</label>
            <select
              value={providerType}
              onChange={(e) => setProviderType(e.target.value as 'local' | 's3')}
              className="w-full text-xs bg-muted/40 p-2 rounded border border-input focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="local">Local Filesystem / Shared Directory</option>
              <option value="s3">S3-Compatible Object Store (MinIO, R2, AWS S3)</option>
            </select>
          </div>

          {providerType === 'local' ? (
            <Input
              label="Local Directory Path"
              placeholder="e.g., C:/Users/name/backup_repo or /mnt/shared_repo"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              required
            />
          ) : (
            <div className="space-y-3">
              <Input
                label="S3 Bucket Name"
                placeholder="e.g., barsa-user-memory"
                value={s3Bucket}
                onChange={(e) => setS3Bucket(e.target.value)}
                required
              />
              <Input
                label="Endpoint URL (Optional for MinIO / R2)"
                placeholder="e.g., http://localhost:9000"
                value={s3Endpoint}
                onChange={(e) => setS3Endpoint(e.target.value)}
              />
              <Input
                label="Region"
                placeholder="us-east-1"
                value={s3Region}
                onChange={(e) => setS3Region(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  label="Access Key ID"
                  placeholder="AKIA..."
                  value={s3AccessKey}
                  onChange={(e) => setS3AccessKey(e.target.value)}
                />
                <Input
                  label="Secret Access Key"
                  placeholder="••••••••••••••••"
                  type="password"
                  value={s3SecretKey}
                  onChange={(e) => setS3SecretKey(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="flex items-center space-x-2 pt-1">
            <input
              type="checkbox"
              id="encrypt-checkbox"
              checked={encryptionEnabled}
              onChange={(e) => setEncryptionEnabled(e.target.checked)}
              className="rounded border-input text-primary focus:ring-primary"
            />
            <label htmlFor="encrypt-checkbox" className="text-xs text-muted-foreground cursor-pointer">
              Enable Client-Side AES-256-GCM Encryption (Zero-Knowledge)
            </label>
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-border">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsAddRemoteOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={!remoteName.trim()}>
              Save Remote
            </Button>
          </div>
        </form>
      </Modal>

      {/* Import Modal */}
      <Modal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        title="Import BMS Portable Package"
        description={`Import a validated BMS JSON package into workspace "${activeWorkspace?.name || 'Selected Workspace'}".`}
      >
        <div className="space-y-4">
          {importStatus && (
            <div
              className={`p-3 text-xs rounded border ${
                importStatus.startsWith('Success')
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-destructive/10 text-destructive border-destructive/20'
              }`}
            >
              {importStatus}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium mb-1">Upload JSON Package File</label>
            <input
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90 cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Or Paste Package JSON Payload</label>
            <textarea
              rows={6}
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='{"schema_version": "0.1", "project": { ... }, "records": [ ... ]}'
              className="w-full font-mono text-xs bg-muted/40 p-2.5 rounded border border-input focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setIsImportOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleImport} isLoading={isImporting} disabled={!importJson.trim()}>
              Validate & Import
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
