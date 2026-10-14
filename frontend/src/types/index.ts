/**
 * TypeScript domain types reflecting BARSA backend APIs.
 */

// ==========================================
// Workspaces & Projects
// ==========================================

export interface Workspace {
  workspace_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export interface Project {
  project_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: 'active' | 'archived' | 'completed' | 'paused';
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

// ==========================================
// BMS Records & Artifacts
// ==========================================

export type RecordType =
  | 'task'
  | 'requirement'
  | 'decision'
  | 'context'
  | 'constraint'
  | 'knowledge'
  | 'checkpoint'
  | 'agent';

export type VerificationStatus = 'verified' | 'unverified' | 'inconclusive' | 'refuted';

export interface BMSRecord {
  record_id: string;
  schema_version: string;
  record_type: RecordType;
  title: string;
  summary: string;
  author: string;
  created_at: string;
  updated_at: string;
  project_id: string;
  workspace_id?: string;
  verification_status: VerificationStatus;
  confidence_score?: number;
  sensitivity?: 'public' | 'internal' | 'confidential' | 'restricted';
  tags: string[];
  attributes: Record<string, unknown>;
  content: string;
  revision: number;
}

export interface Artifact {
  artifact_id: string;
  project_id: string;
  workspace_id: string;
  filename: string;
  content_type: string;
  byte_size: number;
  sha256_hash: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

// ==========================================
// Version Control & DAG
// ==========================================

export interface CommitAuthor {
  agent_id?: string;
  user_id?: string;
  name: string;
  email?: string;
}

export interface MemoryChange {
  record_id: string;
  operation: 'create' | 'update' | 'delete';
  field_changes?: Record<string, { old: unknown; new: unknown }>;
  new_record_state?: BMSRecord;
  old_record_state?: BMSRecord;
}

export interface Commit {
  commit_hash: string;
  project_id: string;
  parent_hashes: string[];
  author: CommitAuthor;
  message: string;
  timestamp: string;
  changes_count?: number;
  changes?: MemoryChange[];
}

export interface Branch {
  name: string;
  head_commit_hash: string;
  is_default: boolean;
  protected?: boolean;
}

export interface StructuredDiff {
  base_commit_hash: string;
  target_commit_hash: string;
  changed_records: Record<string, {
    operation: 'create' | 'update' | 'delete';
    fields: Record<string, { old: unknown; new: unknown }>;
  }>;
}

export interface ConflictItem {
  record_id: string;
  field_name: string;
  base_value: unknown;
  source_value: unknown;
  target_value: unknown;
  is_resolved: boolean;
  resolved_value?: unknown;
}

export interface ReviewComment {
  comment_id: string;
  author_id: string;
  author_name: string;
  body: string;
  timestamp: string;
}

export interface Review {
  review_id: string;
  project_id: string;
  source_branch: string;
  target_branch: string;
  title: string;
  description?: string;
  status: 'pending' | 'approved' | 'rejected' | 'merged';
  author_id: string;
  created_at: string;
  comments: ReviewComment[];
}

// ==========================================
// FalkorDB Knowledge Graph
// ==========================================

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties?: Record<string, unknown>;
}

export interface GraphOverview {
  project_id: string;
  total_nodes: number;
  total_edges: number;
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
  projection_revision: number;
  is_stale: boolean;
}

export interface SubgraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  center_id?: string;
  radius?: number;
}

// ==========================================
// Smart Context Engine (SCE)
// ==========================================

export interface ContextPackage {
  package_id: string;
  project_id: string;
  created_at: string;
  token_budget: number;
  total_tokens: number;
  counting_method: string;
  records_included: number;
  records_omitted: number;
  summary_text: string;
  rendered_context: string;
  records: BMSRecord[];
  graph_freshness?: string;
}

export interface ContextMetrics {
  project_id: string;
  total_requests: number;
  avg_tokens: number;
  avg_latency_ms: number;
  avg_compression_ratio: number;
}

// ==========================================
// Multi-Agent Coordination
// ==========================================

export type AgentState = 'active' | 'idle' | 'busy' | 'offline' | 'disabled';

export interface AgentProfile {
  agent_id: string;
  name: string;
  provider: string;
  model?: string;
  state: AgentState;
  claimed_capabilities: string[];
  verified_capabilities: string[];
  supported_tools: string[];
  current_tasks_count: number;
  last_heartbeat: string;
  created_at: string;
}

export type TaskStatus =
  | 'pending'
  | 'ready'
  | 'running'
  | 'blocked'
  | 'under_review'
  | 'completed'
  | 'cancelled';

export interface CoordinationTask {
  task_id: string;
  project_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_agent_id?: string | null;
  required_capabilities: string[];
  dependencies: string[];
  blockers: string[];
  created_at: string;
  updated_at: string;
  submitted_output?: string | null;
}

export interface CoordinationIssue {
  issue_id: string;
  task_id: string;
  reported_by: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  resolved: boolean;
  created_at: string;
}

export interface CollaborationMessage {
  message_id: string;
  task_id?: string;
  sender_id: string;
  recipient_id?: string;
  message_type: 'info' | 'question' | 'approval_request' | 'handshake';
  content: string;
  timestamp: string;
}

// ==========================================
// Security & Access Control
// ==========================================

export type PrincipalType = 'human' | 'agent' | 'service';
export type WorkspaceRole = 'owner' | 'admin' | 'editor' | 'reviewer' | 'viewer';

export interface AuthenticatedPrincipal {
  principal_id: string;
  principal_type: PrincipalType;
  display_name: string;
  is_superuser: boolean;
  allowed_projects: string[];
  granted_scopes: string[];
  max_sensitivity: string;
}

export interface AgentCredential {
  credential_id: string;
  principal_id: string;
  label?: string;
  key_prefix: string;
  scopes: string[];
  allowed_projects: string[];
  is_active: boolean;
  created_at: string;
  expires_at?: string | null;
  last_used_at?: string | null;
}

export interface AuditEvent {
  event_id: string;
  timestamp: string;
  actor_id: string;
  actor_type: string;
  event_type: string;
  resource_type: string;
  resource_id?: string | null;
  workspace_id?: string | null;
  action: string;
  status: 'success' | 'failure';
  details: Record<string, unknown>;
  ip_address?: string | null;
}

// ==========================================
// System Info & Health
// ==========================================

export interface SystemInfo {
  app_name: string;
  version: string;
  environment: string;
  storage_provider: string;
  falkordb_status: 'connected' | 'disconnected' | 'disabled';
  active_workspaces: number;
  total_projects: number;
}
