import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/utils';
import type { AgentProfile, AgentState } from '@/types';
import { Bot, Plus, ShieldCheck, Wrench } from 'lucide-react';

export function AgentsPage() {
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [provider, setProvider] = useState('anthropic');
  const [model, setModel] = useState('claude-3-5-sonnet');
  const [capabilities, setCapabilities] = useState('memory:read, memory:commit, code:refactor');
  const [tools, setTools] = useState('mcp_barsa_tools, bash, file_editor');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadAgents = async () => {
    setIsLoading(true);
    try {
      const list = await api.listAgents();
      setAgents(list);
    } catch {
      setAgents([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      await api.registerAgent({
        name: name.trim(),
        provider: provider.trim(),
        model: model.trim() || undefined,
        claimed_capabilities: capabilities.split(',').map((s) => s.trim()).filter(Boolean),
        supported_tools: tools.split(',').map((s) => s.trim()).filter(Boolean),
        state: 'active' as AgentState,
      });
      await loadAgents();
      setIsRegisterOpen(false);
      setName('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to register agent');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agent Registry & Coordination</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Registered AI agents, claimed vs verified capabilities, and task workloads.
          </p>
        </div>
        <Button onClick={() => setIsRegisterOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          Register Agent
        </Button>
      </div>

      {isLoading ? (
        <LoadingSpinner text="Retrieving agent registry..." />
      ) : agents.length === 0 ? (
        <EmptyState
          icon={<Bot className="h-10 w-10 text-muted-foreground" />}
          title="No Agents Registered"
          description="Register your Claude, GPT-4, or local AI copilot to start assigning collaborative tasks."
          actionLabel="Register Agent"
          onAction={() => setIsRegisterOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => {
            const isLive = agent.state === 'active' || agent.state === 'busy';
            return (
              <Card key={agent.agent_id} className="flex flex-col justify-between">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold flex items-center">
                        <Bot className="h-4 w-4 mr-2 text-primary" />
                        {agent.display_name || (agent as any).name || agent.agent_id}
                      </CardTitle>
                      <CardDescription className="text-xs mt-1">
                        Provider: <strong className="text-foreground capitalize">{agent.provider}</strong> •{' '}
                        {agent.model || 'Default'}
                      </CardDescription>
                    </div>
                    <Badge variant={isLive ? 'success' : 'secondary'} className="capitalize text-[10px]">
                      {agent.state}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="text-xs space-y-1.5 bg-muted/40 p-2.5 rounded border border-border">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">ID:</span>
                      <span className="font-mono text-[11px] truncate max-w-[140px]">{agent.agent_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Workload:</span>
                      <span className="font-medium text-foreground">{agent.current_tasks_count} active tasks</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last Heartbeat:</span>
                      <span>{formatDate(agent.last_heartbeat)}</span>
                    </div>
                  </div>

                  <div>
                    <h5 className="text-[11px] font-semibold text-muted-foreground uppercase flex items-center mb-1">
                      <ShieldCheck className="h-3 w-3 mr-1 text-emerald-400" />
                      Verified Capabilities
                    </h5>
                    <div className="flex flex-wrap gap-1">
                      {agent.verified_capabilities.length > 0 ? (
                        agent.verified_capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded text-[10px] font-mono"
                          >
                            {cap}
                          </span>
                        ))
                      ) : (
                        <span className="text-[11px] text-muted-foreground">None verified yet</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <h5 className="text-[11px] font-semibold text-muted-foreground uppercase flex items-center mb-1">
                      <Wrench className="h-3 w-3 mr-1 text-primary" />
                      Supported Tools
                    </h5>
                    <div className="flex flex-wrap gap-1">
                      {agent.supported_tools.map((tool) => (
                        <span
                          key={tool}
                          className="bg-accent text-accent-foreground px-1.5 py-0.5 rounded text-[10px] font-mono"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Register Agent Modal */}
      <Modal
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        title="Register AI Agent Profile"
        description="Declare provider, model, and capabilities for automated task scheduling."
      >
        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Agent Name *</label>
            <Input
              placeholder="e.g. Claude Code Reviewer"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Provider *</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs"
              >
                <option value="anthropic">Anthropic</option>
                <option value="openai">OpenAI</option>
                <option value="google">Google</option>
                <option value="local">Local Model</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Model Name</label>
              <Input
                placeholder="e.g. claude-3-5-sonnet"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Claimed Capabilities (comma separated)</label>
            <Input
              placeholder="memory:read, memory:commit, code:refactor"
              value={capabilities}
              onChange={(e) => setCapabilities(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Supported Tools (comma separated)</label>
            <Input
              placeholder="mcp_barsa_tools, bash, file_editor"
              value={tools}
              onChange={(e) => setTools(e.target.value)}
            />
          </div>

          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsRegisterOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Register Agent
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
