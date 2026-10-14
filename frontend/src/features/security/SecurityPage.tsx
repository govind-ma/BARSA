import { useEffect, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { formatDate } from '@/lib/utils';
import type { AuditEvent } from '@/types';
import {
  Key,
  RefreshCw,
  Copy,
  Check,
  AlertTriangle,
  History,
  Lock,
} from 'lucide-react';

export function SecurityPage() {
  const { principal } = useApp();
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Key creation state
  const [isCreateKeyOpen, setIsCreateKeyOpen] = useState(false);
  const [agentId, setAgentId] = useState('');
  const [label, setLabel] = useState('');
  const [scopes, setScopes] = useState('memory:read, memory:commit');
  const [newRawKey, setNewRawKey] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadSecurityData = async () => {
    setIsLoading(true);
    try {
      const [events] = await Promise.allSettled([api.listAuditEvents(50)]);
      if (events.status === 'fulfilled') setAuditEvents(events.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSecurityData();
  }, []);

  const handleCreateCredential = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentId.trim()) return;
    setIsSubmitting(true);
    try {
      const res = await api.createAgentCredential({
        principal_id: agentId.trim(),
        label: label.trim() || undefined,
        scopes: scopes.split(',').map((s) => s.trim()).filter(Boolean),
      });
      setNewRawKey(res.raw_key);
      await loadSecurityData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to generate credential');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyRawKey = () => {
    if (!newRawKey) return;
    navigator.clipboard.writeText(newRawKey);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Security & Access Control</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Phase 10 local-first identity, agent credentials, RBAC, and immutable audit trails.
          </p>
        </div>
        <Button onClick={() => { setIsCreateKeyOpen(true); setNewRawKey(null); }} size="sm">
          <Key className="h-4 w-4 mr-1.5" />
          Issue Agent API Key
        </Button>
      </div>

      {/* Authenticated Identity Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center">
            <Lock className="h-4 w-4 mr-2 text-primary" />
            Current Authenticated Principal
          </CardTitle>
          <CardDescription>Verified session identity driving central authorization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 bg-muted/40 rounded border border-border">
              <span className="text-muted-foreground block mb-1">Principal ID</span>
              <span className="font-mono font-medium text-foreground">{principal?.principal_id || 'local-owner'}</span>
            </div>
            <div className="p-3 bg-muted/40 rounded border border-border">
              <span className="text-muted-foreground block mb-1">Display Name</span>
              <span className="font-medium text-foreground">{principal?.display_name || 'Local Desktop Owner'}</span>
            </div>
            <div className="p-3 bg-muted/40 rounded border border-border">
              <span className="text-muted-foreground block mb-1">Principal Type</span>
              <Badge variant="outline" className="capitalize text-[10px]">
                {principal?.principal_type || 'human'}
              </Badge>
            </div>
            <div className="p-3 bg-muted/40 rounded border border-border">
              <span className="text-muted-foreground block mb-1">Superuser Clearance</span>
              <Badge variant={principal?.is_superuser ? 'default' : 'secondary'} className="text-[10px]">
                {principal?.is_superuser ? 'SUPERUSER' : 'STANDARD'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base font-semibold flex items-center">
              <History className="h-4 w-4 mr-2 text-primary" />
              Immutable Security Audit Events
            </CardTitle>
            <CardDescription>Append-only forensic trail from the SQLite audit_events table</CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={loadSecurityData} isLoading={isLoading}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {auditEvents.length === 0 ? (
            <p className="text-xs text-muted-foreground py-8 text-center">
              No audit events recorded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs" aria-label="Security Audit Log">
                <thead className="border-b border-border bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="p-3">Timestamp</th>
                    <th className="p-3">Actor</th>
                    <th className="p-3">Event Type</th>
                    <th className="p-3">Resource</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {auditEvents.map((evt) => (
                    <tr key={evt.event_id} className="hover:bg-accent/40">
                      <td className="p-3 font-mono text-[11px] text-muted-foreground">
                        {formatDate(evt.timestamp)}
                      </td>
                      <td className="p-3 font-mono font-medium text-foreground">{evt.actor_id}</td>
                      <td className="p-3">
                        <span className="font-mono text-[11px] bg-muted px-1.5 py-0.5 rounded">
                          {evt.event_type}
                        </span>
                      </td>
                      <td className="p-3 text-muted-foreground">
                        {evt.resource_type} {evt.resource_id ? `(${evt.resource_id})` : ''}
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={evt.status === 'success' ? 'success' : 'destructive'}
                          className="text-[10px]"
                        >
                          {evt.status}
                        </Badge>
                      </td>
                      <td className="p-3 font-mono text-[10px] text-muted-foreground max-w-xs truncate">
                        {JSON.stringify(evt.details)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Issue Agent Credential Modal */}
      <Modal
        isOpen={isCreateKeyOpen}
        onClose={() => setIsCreateKeyOpen(false)}
        title={newRawKey ? 'Agent API Key Generated' : 'Issue Agent API Key'}
        description={
          newRawKey
            ? 'Store this secret securely now. It will NEVER be displayed again!'
            : 'Generate a high-entropy barsa_ak_... credential with bounded scopes.'
        }
      >
        {newRawKey ? (
          <div className="space-y-4">
            <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start space-x-3 text-amber-300 text-xs">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-amber-400" />
              <div>
                <strong className="block font-semibold">One-Time Secret Key Display</strong>
                BARSA never stores raw API keys. Only a salted SHA-256 hash is retained on disk. If lost, you must rotate or reissue the credential.
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-muted-foreground block">
                Generated API Key:
              </label>
              <div className="flex items-center space-x-2">
                <input
                  readOnly
                  value={newRawKey}
                  className="flex-1 font-mono text-xs bg-muted/60 p-2.5 rounded border border-border text-foreground select-all"
                />
                <Button size="sm" onClick={handleCopyRawKey}>
                  {isCopied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            <div className="flex justify-end pt-3">
              <Button onClick={() => setIsCreateKeyOpen(false)}>Done</Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleCreateCredential} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1">Agent Principal ID *</label>
              <Input
                placeholder="e.g. agt_claude_reviewer"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Credential Label</label>
              <Input
                placeholder="e.g. Claude 3.5 Sonnet Local Desktop"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Capability Scopes (comma separated)</label>
              <Input
                placeholder="memory:read, memory:commit, branch:manage"
                value={scopes}
                onChange={(e) => setScopes(e.target.value)}
                required
              />
            </div>

            <div className="flex justify-end space-x-2 pt-3">
              <Button type="button" variant="outline" onClick={() => setIsCreateKeyOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isSubmitting}>
                Generate Key
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
