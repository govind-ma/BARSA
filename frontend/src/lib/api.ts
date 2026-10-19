import type {
  AgentCredential,
  AgentProfile,
  Artifact,
  AuditEvent,
  AuthenticatedPrincipal,
  BMSRecord,
  Branch,
  CollaborationMessage,
  Commit,
  ConflictItem,
  ContextMetrics,
  ContextPackage,
  CoordinationIssue,
  CoordinationTask,
  GraphOverview,
  GraphResumeResponse,
  Project,
  Review,
  StructuredDiff,
  SubgraphResponse,
  SystemInfo,
  Workspace,
} from '@/types';

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function normalizeWorkspace(w: any): Workspace {
  if (!w) return w;
  const id = w.workspace_id || w.id || '';
  return {
    ...w,
    id,
    workspace_id: id,
  };
}

function normalizeProject(p: any): Project {
  if (!p) return p;
  const id = p.project_id || p.id || '';
  const wid = p.workspace_id || '';
  return {
    ...p,
    id,
    project_id: id,
    workspace_id: wid,
  };
}

function normalizeRecord(r: any): BMSRecord {
  if (!r) return r;
  const inner = r.record || r;
  const id = r.record_id || inner.id || inner.record_id || '';
  const title =
    inner.title ||
    (Array.isArray(inner.completed_actions) && inner.completed_actions.length > 0 ? inner.completed_actions[0] : null) ||
    (inner.content ? (inner.content.length > 50 ? inner.content.substring(0, 47) + '...' : inner.content) : null) ||
    inner.decision ||
    inner.next_action ||
    id;
  const summary = inner.summary || inner.decision || inner.rationale || inner.content || inner.description || '';
  const author = inner.created_by || inner.author || inner.author_id || 'system';
  const status = inner.verification_status || inner.status || 'verified';

  return {
    ...inner,
    ...r,
    id,
    record_id: id,
    title,
    summary,
    author,
    verification_status: status,
    schema_version: inner.schema_version || '0.1',
    record_type: r.record_type || inner.record_type || 'knowledge',
    created_at: inner.created_at || new Date().toISOString(),
    updated_at: inner.updated_at || inner.created_at || new Date().toISOString(),
    project_id: r.project_id || inner.project_id || '',
  };
}

function normalizeAgent(a: any): AgentProfile {
  if (!a) return a;
  const name = a.display_name || a.name || a.agent_id || 'AI Agent';
  return {
    ...a,
    name,
    display_name: name,
    provider: a.provider || 'anthropic',
    state: a.state || a.status || 'active',
    claimed_capabilities: a.claimed_capabilities || [],
    verified_capabilities: a.verified_capabilities || [],
    supported_tools: a.supported_tools || [],
    current_tasks_count: a.current_tasks_count || (a.active_tasks ? a.active_tasks.length : 0),
    last_heartbeat: a.last_heartbeat || a.updated_at || new Date().toISOString(),
    created_at: a.created_at || new Date().toISOString(),
  };
}

function normalizeCommit(c: any): Commit {
  if (!c) return c;
  const commit_hash = c.commit_hash || c.commit_id || c.hash || c.id || '';
  const parent_hashes = c.parent_hashes || c.parent_commit_ids || [];
  const authorName = c.author?.name || c.author_id || 'AI Agent';
  const timestamp = c.timestamp || c.created_at || new Date().toISOString();
  return {
    ...c,
    commit_hash,
    project_id: c.project_id || '',
    parent_hashes: Array.isArray(parent_hashes) ? parent_hashes : [],
    author: {
      name: authorName,
      email: c.author?.email || `${authorName.toLowerCase()}@barsa.local`,
      role: c.author?.role || c.author_type || 'agent',
    },
    message: c.message || 'Updated project memory state',
    timestamp,
    changes_count: c.changes_count || (c.changes ? c.changes.length : 0),
    changes: c.changes || [],
  };
}

function normalizeBranch(b: any): Branch {
  if (!b) return b;
  return {
    ...b,
    name: b.name || 'main',
    head_commit_hash: b.head_commit_hash || b.head_commit_id || '',
    is_default: Boolean(b.is_default ?? (b.name === 'main')),
    protected: Boolean(b.protected),
  };
}

class ApiClient {
  private baseUrl = '';
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      sessionStorage.setItem('barsa_auth_token', token);
    } else {
      sessionStorage.removeItem('barsa_auth_token');
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = sessionStorage.getItem('barsa_auth_token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: unknown;
      let errorMessage = `API Request failed with status ${response.status}`;
      try {
        errorData = await response.json();
        if (typeof errorData === 'object' && errorData !== null && 'detail' in errorData) {
          const detail = (errorData as { detail: unknown }).detail;
          if (Array.isArray(detail)) {
            errorMessage = detail
              .map((d: { loc?: string[]; msg?: string }) => `${d.loc ? d.loc.slice(-1)[0] + ': ' : ''}${d.msg || ''}`)
              .join(', ');
          } else {
            errorMessage = String(detail);
          }
        }
      } catch {
        // Body was not json
      }
      throw new ApiError(response.status, errorMessage, errorData);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // System & Health
  async getHealth(): Promise<{ status: string }> {
    return this.request('/health');
  }

  async getInfo(): Promise<SystemInfo> {
    return this.request('/api/v1/info');
  }

  // Workspaces
  async listWorkspaces(): Promise<Workspace[]> {
    const list = await this.request<any[]>('/api/v1/workspaces');
    return Array.isArray(list) ? list.map(normalizeWorkspace) : [];
  }

  async getWorkspace(id: string): Promise<Workspace> {
    if (!id || id === 'undefined') throw new ApiError(404, 'Workspace ID required');
    const ws = await this.request<any>(`/api/v1/workspaces/${id}`);
    return normalizeWorkspace(ws);
  }

  async createWorkspace(data: { name: string; description?: string; owner_id?: string }): Promise<Workspace> {
    const res = await this.request<any>('/api/v1/workspaces', {
      method: 'POST',
      body: JSON.stringify({
        owner_id: 'u-default',
        ...data,
      }),
    });
    return normalizeWorkspace(res);
  }

  async deleteWorkspace(id: string, cascade = true): Promise<void> {
    if (!id || id === 'undefined') return;
    const query = cascade ? '?cascade=true' : '';
    return this.request(`/api/v1/workspaces/${id}${query}`, { method: 'DELETE' });
  }

  // Projects
  async listProjects(workspaceId?: string | null): Promise<Project[]> {
    const url = workspaceId && workspaceId !== 'undefined'
      ? `/api/v1/workspaces/${workspaceId}/projects`
      : `/api/v1/projects`;
    const list = await this.request<any[]>(url);
    return Array.isArray(list) ? list.map(normalizeProject) : [];
  }

  async getProject(id: string): Promise<Project> {
    if (!id || id === 'undefined') throw new ApiError(404, 'Project ID required');
    const proj = await this.request<any>(`/api/v1/projects/${id}`);
    return normalizeProject(proj);
  }

  async createProject(workspaceId: string, data: { name: string; description?: string }): Promise<Project> {
    if (!workspaceId || workspaceId === 'undefined') throw new ApiError(400, 'Workspace ID required');
    const res = await this.request<any>(`/api/v1/workspaces/${workspaceId}/projects`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return normalizeProject(res);
  }

  async deleteProject(id: string): Promise<void> {
    if (!id || id === 'undefined') return;
    return this.request(`/api/v1/projects/${id}`, { method: 'DELETE' });
  }

  // Memory & BMS Records
  async listRecords(projectId?: string | null, recordType?: string): Promise<BMSRecord[]> {
    if (!projectId || projectId === 'undefined') return [];
    const query = recordType ? `?record_type=${encodeURIComponent(recordType)}` : '';
    const list = await this.request<any[]>(`/api/v1/projects/${projectId}/records${query}`);
    return Array.isArray(list) ? list.map(normalizeRecord) : [];
  }

  async getRecord(projectId: string, recordId: string): Promise<BMSRecord> {
    if (!projectId || !recordId || projectId === 'undefined' || recordId === 'undefined') throw new ApiError(404, 'Record not found');
    const r = await this.request<any>(`/api/v1/projects/${projectId}/records/${recordId}`);
    return normalizeRecord(r);
  }

  async createRecord(projectId: string, record: Partial<BMSRecord>): Promise<BMSRecord> {
    return this.request(`/api/v1/projects/${projectId}/records`, {
      method: 'POST',
      body: JSON.stringify(record),
    });
  }

  async updateRecord(projectId: string, recordId: string, record: Partial<BMSRecord>): Promise<BMSRecord> {
    return this.request(`/api/v1/projects/${projectId}/records/${recordId}`, {
      method: 'PUT',
      body: JSON.stringify(record),
    });
  }

  async validateRecord(record: unknown): Promise<{ is_valid: boolean; valid: boolean; errors: string[] }> {
    const res = await this.request<any>('/api/v1/bms/validate', {
      method: 'POST',
      body: JSON.stringify(record),
    });
    const isValid = Boolean(res.valid ?? res.is_valid);
    return {
      is_valid: isValid,
      valid: isValid,
      errors: res.errors || [],
    };
  }

  // Artifacts
  async listArtifacts(projectId: string): Promise<Artifact[]> {
    return this.request(`/api/v1/projects/${projectId}/artifacts`);
  }

  async getArtifact(projectId: string, artifactId: string): Promise<Artifact> {
    return this.request(`/api/v1/projects/${projectId}/artifacts/${artifactId}`);
  }

  // Version Control
  async listCommits(projectId: string): Promise<Commit[]> {
    const list = await this.request<any[]>(`/api/v1/projects/${projectId}/versioning/history`);
    return Array.isArray(list) ? list.map(normalizeCommit) : [];
  }

  async getCommit(projectId: string, commitHash: string): Promise<Commit> {
    const c = await this.request<any>(`/api/v1/projects/${projectId}/versioning/commits/${commitHash}`);
    return normalizeCommit(c);
  }

  async createCommit(projectId: string, data: { message: string; author: { name: string; email?: string }; changes: unknown[] }): Promise<Commit> {
    const res = await this.request<any>(`/api/v1/projects/${projectId}/versioning/commits`, {
      method: 'POST',
      body: JSON.stringify({
        message: data.message,
        branch: 'main',
        author_id: data.author?.name || 'dashboard-user',
        changes: data.changes || [],
      }),
    });
    return normalizeCommit(res);
  }

  async listBranches(projectId: string): Promise<Branch[]> {
    const list = await this.request<any[]>(`/api/v1/projects/${projectId}/versioning/branches`);
    return Array.isArray(list) ? list.map(normalizeBranch) : [];
  }

  async createBranch(projectId: string, data: { name: string; source_branch?: string }): Promise<Branch> {
    const res = await this.request<any>(`/api/v1/projects/${projectId}/versioning/branches`, {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        start_commit_id: null,
      }),
    });
    return normalizeBranch(res);
  }

  async getDiff(projectId: string, baseCommitHash: string, targetCommitHash: string): Promise<StructuredDiff> {
    return this.request(
      `/api/v1/projects/${projectId}/versioning/diff?from_commit=${baseCommitHash}&to_commit=${targetCommitHash}`
    );
  }

  async listConflicts(projectId: string): Promise<ConflictItem[]> {
    return this.request(`/api/v1/projects/${projectId}/versioning/conflicts`);
  }

  async listReviews(projectId: string): Promise<Review[]> {
    return this.request(`/api/v1/projects/${projectId}/versioning/merge-proposals`);
  }

  async createReview(projectId: string, data: { source_branch: string; target_branch: string; title: string; description?: string }): Promise<Review> {
    return this.request(`/api/v1/projects/${projectId}/versioning/merge-proposals`, {
      method: 'POST',
      body: JSON.stringify({
        source_branch: data.source_branch,
        target_branch: data.target_branch,
        title: data.title,
        description: data.description || '',
        author_id: 'dashboard-user',
      }),
    });
  }

  async mergeBranches(projectId: string, data: { source_branch: string; target_branch: string; author: { name: string } }): Promise<{ success: boolean; commit_hash?: string }> {
    return this.request(`/api/v1/projects/${projectId}/versioning/merge`, {
      method: 'POST',
      body: JSON.stringify({
        author_id: data.author?.name || 'dashboard-user',
      }),
    });
  }

  // Knowledge Graph
  async getGraphOverview(projectId: string): Promise<GraphOverview> {
    try {
      const res = await this.request<any>(`/api/v1/projects/${projectId}/graph/overview`);
      const nodes = [
        ...(res.active_tasks || []).map((t: any) => ({
          id: t.raw_id || t.id,
          label: t.properties?.title || t.raw_id || t.id,
          type: 'Task',
          status: t.properties?.status || 'todo',
          data: t.properties || {},
        })),
        ...(res.approved_decisions || []).map((d: any) => ({
          id: d.raw_id || d.id,
          label: d.properties?.title || d.raw_id || d.id,
          type: 'Decision',
          status: d.properties?.status || 'approved',
          data: d.properties || {},
        })),
        ...(res.requirements || []).map((r: any) => ({
          id: r.raw_id || r.id,
          label: r.properties?.title || r.raw_id || r.id,
          type: 'Capability',
          status: 'active',
          data: r.properties || {},
        })),
        ...(res.relevant_artifacts || []).map((a: any) => ({
          id: a.raw_id || a.id,
          label: a.properties?.title || a.raw_id || a.id,
          type: 'Artifact',
          status: 'verified',
          data: a.properties || {},
        })),
      ];
      if (res.latest_checkpoint) {
        const cp = res.latest_checkpoint;
        nodes.push({
          id: cp.raw_id || cp.id,
          label: cp.raw_id || cp.id,
          type: 'Checkpoint',
          status: cp.properties?.status || 'active',
          data: cp.properties || {},
        });
      }
      return {
        total_nodes: res.projection_status?.node_count || nodes.length,
        total_edges: res.projection_status?.relationship_count || 0,
        nodes,
        edges: [],
        projection_status: res.projection_status,
      } as any;
    } catch {
      return this.request(`/api/v1/graph/${projectId}/overview`);
    }
  }

  async getSubgraph(projectId: string, _centerId?: string, _radius?: number): Promise<SubgraphResponse> {
    try {
      const res = await this.request<any>(`/api/v1/projects/${projectId}/graph/subgraph`);
      if (res && Array.isArray(res.nodes)) {
        return res as SubgraphResponse;
      }
    } catch {
      // Fallback to overview if subgraph fails
    }
    const overview = await this.getGraphOverview(projectId);
    return {
      nodes: (overview as any).nodes || [],
      edges: (overview as any).edges || [],
    } as any;
  }

  async getGraphStatus(): Promise<{ status: string; is_connected: boolean }> {
    try {
      return await this.request('/api/v1/graph/status');
    } catch {
      return { status: 'healthy', is_connected: true };
    }
  }

  async rebuildGraph(projectId: string): Promise<{ success: boolean; message: string }> {
    try {
      const res = await this.request<any>(`/api/v1/projects/${projectId}/graph/rebuild`, { method: 'POST' });
      return { success: true, message: res.message || 'Graph successfully rebuilt' };
    } catch {
      return this.request(`/api/v1/graph/${projectId}/rebuild`, { method: 'POST' });
    }
  }

  async getGraphResume(projectId: string, agentId?: string): Promise<GraphResumeResponse> {
    const query = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : '';
    return this.request(`/api/v1/projects/${projectId}/graph/resume${query}`);
  }

  // Smart Context Engine
  async resumeContext(projectId: string, tokenBudget = 8000): Promise<ContextPackage> {
    return this.request(`/api/v1/context/${projectId}/resume`, {
      method: 'POST',
      body: JSON.stringify({ token_budget: tokenBudget }),
    });
  }

  async getContextMetrics(projectId: string): Promise<ContextMetrics> {
    return this.request(`/api/v1/context/${projectId}/metrics`);
  }

  // Multi-Agent Coordination
  async listAgents(): Promise<AgentProfile[]> {
    const list = await this.request<any[]>('/api/v1/coordination/agents');
    return Array.isArray(list) ? list.map(normalizeAgent) : [];
  }

  async registerAgent(data: any): Promise<AgentProfile> {
    const rawName = data.display_name || data.name || 'AI Agent';
    const agentId = data.agent_id || `agt_${rawName.toLowerCase().replace(/[^a-z0-9_]/g, '_')}_${Date.now().toString(36)}`;
    const payload = {
      agent_id: agentId,
      display_name: rawName,
      provider: data.provider || 'anthropic',
      model: data.model || 'claude-3-7-sonnet',
      claimed_capabilities: data.claimed_capabilities || ['reasoning', 'coding'],
      verified_capabilities: data.verified_capabilities || [],
      supported_tools: data.supported_tools || ['bms_memory', 'git_versioning'],
      allowed_projects: data.allowed_projects || ['*'],
      maximum_concurrent_tasks: data.maximum_concurrent_tasks || 2,
      metadata: data.metadata || {},
    };
    return this.request('/api/v1/coordination/agents/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async listTasks(projectId?: string): Promise<CoordinationTask[]> {
    const query = projectId ? `?project_id=${projectId}` : '';
    return this.request(`/api/v1/coordination/tasks${query}`);
  }

  async createTask(data: Partial<CoordinationTask>): Promise<CoordinationTask> {
    const payload = {
      task_id: data.task_id || `task_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      ...data,
    };
    return this.request('/api/v1/coordination/tasks', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async claimTask(taskId: string, agentId: string): Promise<{ success: boolean; task: CoordinationTask }> {
    return this.request(`/api/v1/coordination/tasks/${taskId}/claim`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId }),
    });
  }

  async listIssues(): Promise<CoordinationIssue[]> {
    return this.request('/api/v1/coordination/issues');
  }

  async listMessages(): Promise<CollaborationMessage[]> {
    return this.request('/api/v1/coordination/messages');
  }

  // Security & Identity
  async getCurrentPrincipal(): Promise<AuthenticatedPrincipal> {
    return this.request('/api/v1/security/me');
  }

  async login(username: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const res = await this.request<{ access_token: string; token_type: string }>('/api/v1/security/users/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    if (res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  async register(username: string, password: string, email?: string): Promise<{ principal_id: string; username: string }> {
    return this.request('/api/v1/security/users/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email }),
    });
  }

  async createAgentCredential(data: { principal_id: string; label?: string; scopes: string[]; allowed_projects?: string[] }): Promise<{ credential_id: string; raw_key: string }> {
    return this.request(`/api/v1/security/agents/${data.principal_id}/credentials`, {
      method: 'POST',
      body: JSON.stringify({
        agent_id: data.principal_id,
        ...data,
      }),
    });
  }

  async listAgentCredentials(agentId: string): Promise<AgentCredential[]> {
    return this.request(`/api/v1/security/agents/${agentId}/credentials`);
  }

  async revokeCredential(credentialId: string): Promise<{ success: boolean }> {
    return this.request(`/api/v1/security/credentials/${credentialId}/revoke`, { method: 'POST' });
  }

  async listAuditEvents(limit = 50): Promise<AuditEvent[]> {
    return this.request(`/api/v1/security/audit-events?limit=${limit}`);
  }

  // Package Export & Import
  async exportProject(projectId: string): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/projects/${projectId}/export`);
  }

  async importPackage(workspaceId: string, pkg: Record<string, unknown>): Promise<{ success: boolean; project_id: string }> {
    return this.request(`/api/v1/workspaces/${workspaceId}/import`, {
      method: 'POST',
      body: JSON.stringify(pkg),
    });
  }

  // Cloud Synchronization (BYOS - Phase 13)
  async listRemotes(projectId: string): Promise<import('@/types').RemoteResponse[]> {
    return this.request(`/api/v1/sync/remotes?project_id=${projectId}`);
  }

  async createRemote(projectId: string, data: Record<string, unknown>): Promise<import('@/types').RemoteResponse> {
    return this.request(`/api/v1/sync/remotes?project_id=${projectId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteRemote(remoteId: string): Promise<void> {
    return this.request(`/api/v1/sync/remotes/${remoteId}`, { method: 'DELETE' });
  }

  async pushRemote(remoteId: string, branch = 'main', force = false, passphrase?: string): Promise<import('@/types').SyncResult> {
    const params = new URLSearchParams({ branch, force: String(force) });
    if (passphrase) params.append('passphrase', passphrase);
    return this.request(`/api/v1/sync/remotes/${remoteId}/push?${params.toString()}`, { method: 'POST' });
  }

  async pullRemote(remoteId: string, branch = 'main', passphrase?: string): Promise<import('@/types').SyncResult> {
    const params = new URLSearchParams({ branch });
    if (passphrase) params.append('passphrase', passphrase);
    return this.request(`/api/v1/sync/remotes/${remoteId}/pull?${params.toString()}`, { method: 'POST' });
  }

  async getRemoteStatus(remoteId: string, branch = 'main', passphrase?: string): Promise<import('@/types').SyncStatusReport> {
    const params = new URLSearchParams({ branch });
    if (passphrase) params.append('passphrase', passphrase);
    return this.request(`/api/v1/sync/remotes/${remoteId}/status?${params.toString()}`);
  }

  async getRemoteHistory(remoteId: string, limit = 20): Promise<Record<string, unknown>[]> {
    return this.request(`/api/v1/sync/remotes/${remoteId}/history?limit=${limit}`);
  }

  async getRemoteConflicts(remoteId: string): Promise<Record<string, unknown>[]> {
    return this.request(`/api/v1/sync/remotes/${remoteId}/conflicts`);
  }
}

export const api = new ApiClient();
export { ApiError };
