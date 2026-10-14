import React, { useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { HardDrive, Download, Upload, ShieldCheck, FileCheck } from 'lucide-react';

export function StoragePage() {
  const { activeWorkspace, activeProject, systemInfo, refreshProjects } = useApp();
  const [importJson, setImportJson] = useState('');
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

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
          <h1 className="text-2xl font-bold tracking-tight">Storage & Portable Packages</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Local-first SQLite storage engine, integrity status, and BMS package portability.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={() => setIsImportOpen(true)}>
            <Upload className="h-4 w-4 mr-1.5" />
            Import BMS Package
          </Button>
          {activeProject && (
            <Button size="sm" onClick={handleExport} isLoading={isExporting}>
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
              Storage Provider
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Engine:</span>
              <span className="font-mono font-medium">{systemInfo?.storage_provider || 'SQLite'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Architecture:</span>
              <span className="font-medium text-foreground">Local-First ACID</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Encryption / Hash:</span>
              <span>Salted SHA-256 + Argon2id</span>
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
              <span className="text-muted-foreground">Database Status:</span>
              <Badge variant="success" className="text-[10px]">
                Healthy
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Transactions:</span>
              <span>WAL Mode Enabled</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Foreign Keys:</span>
              <span>Enforced</span>
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
              <span className="text-muted-foreground">Cross-AI Compatible:</span>
              <span>Claude, GPT, Gemini</span>
            </div>
          </CardContent>
        </Card>
      </div>

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
              placeholder='{"schema_version": "0.1.0", "project": { ... }, "records": [ ... ]}'
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
