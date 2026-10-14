import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AppProvider } from '@/app/AppContext';
import { DashboardHome } from '@/features/dashboard/DashboardHome';
import { WorkspacesPage } from '@/features/workspaces/WorkspacesPage';
import { ProjectsPage } from '@/features/projects/ProjectsPage';
import { ProjectDetailPage } from '@/features/projects/ProjectDetailPage';
import { MemoryExplorerPage } from '@/features/memory/MemoryExplorerPage';
import { VersionControlPage } from '@/features/versioning/VersionControlPage';
import { GraphExplorerPage } from '@/features/graph/GraphExplorerPage';
import { AgentsPage } from '@/features/agents/AgentsPage';
import { TasksPage } from '@/features/coordination/TasksPage';
import { SecurityPage } from '@/features/security/SecurityPage';
import { StoragePage } from '@/features/storage/StoragePage';
import { Sidebar } from '@/components/layout/Sidebar';
import { api, ApiError } from '@/lib/api';

// Realistic fixtures
const mockWorkspace = {
  workspace_id: 'ws_eng_1',
  name: 'Engineering Workspace',
  description: 'Core Engineering team memory',
  created_at: '2026-10-14T10:00:00Z',
  updated_at: '2026-10-14T10:00:00Z',
};

const mockProject = {
  project_id: 'proj_api_1',
  workspace_id: 'ws_eng_1',
  name: 'API Redesign',
  description: 'FastAPI memory backend overhaul',
  status: 'active' as const,
  created_at: '2026-10-14T11:00:00Z',
  updated_at: '2026-10-14T11:00:00Z',
};

const mockRecord = {
  record_id: 'rec_bms_100',
  schema_version: '0.1.0',
  record_type: 'decision' as const,
  title: 'SQLite Local Engine Adoption',
  summary: 'Adopted embedded SQLite for zero-cloud requirement',
  author: 'claude-architect',
  created_at: '2026-10-14T12:00:00Z',
  updated_at: '2026-10-14T12:00:00Z',
  project_id: 'proj_api_1',
  verification_status: 'verified' as const,
  tags: ['storage', 'decision'],
  attributes: {},
  content: 'Comprehensive ADR details regarding SQLite WAL mode.',
  revision: 1,
};

const mockCommit = {
  commit_hash: 'a1b2c3d4e5f6',
  project_id: 'proj_api_1',
  parent_hashes: [],
  author: { name: 'Alice Agent', email: 'alice@barsa.ai' },
  message: 'feat: add initial SQLite schema',
  timestamp: '2026-10-14T12:30:00Z',
};

const mockBranch = {
  name: 'main',
  head_commit_hash: 'a1b2c3d4e5f6',
  is_default: true,
};

const mockAgent = {
  agent_id: 'agt_qa_1',
  name: 'QA Copilot',
  provider: 'anthropic',
  model: 'claude-3-5-sonnet',
  state: 'active' as const,
  claimed_capabilities: ['memory:read'],
  verified_capabilities: ['memory:read'],
  supported_tools: ['bash'],
  current_tasks_count: 1,
  last_heartbeat: '2026-10-14T13:00:00Z',
  created_at: '2026-10-14T10:00:00Z',
};

const mockTask = {
  task_id: 'task_coord_1',
  project_id: 'proj_api_1',
  title: 'Audit credential rotation endpoints',
  description: 'Verify HMAC comparison against timing leaks',
  status: 'running' as const,
  priority: 'high' as const,
  assigned_agent_id: 'agt_qa_1',
  required_capabilities: ['memory:read'],
  dependencies: [],
  blockers: [],
  created_at: '2026-10-14T13:10:00Z',
  updated_at: '2026-10-14T13:10:00Z',
};

const mockGraphOverview = {
  project_id: 'proj_api_1',
  total_nodes: 12,
  total_edges: 18,
  node_counts: { Decision: 4, Task: 8 },
  edge_counts: { DEPENDS_ON: 10, IMPLEMENTS: 8 },
  projection_revision: 5,
  is_stale: false,
};

const mockSubgraph = {
  nodes: [
    { id: 'proj_api_1', label: 'API Redesign', type: 'Project', properties: {} },
    { id: 'rec_bms_100', label: 'SQLite Decision', type: 'Decision', properties: { status: 'approved' } },
  ],
  edges: [
    { id: 'edge_1', source: 'rec_bms_100', target: 'proj_api_1', type: 'REFERENCES' },
  ],
};

const mockPrincipal = {
  principal_id: 'local-owner',
  principal_type: 'human' as const,
  display_name: 'Local Desktop Owner',
  is_superuser: true,
  allowed_projects: ['*'],
  granted_scopes: ['admin:*'],
  max_sensitivity: 'restricted',
};

const mockSystemInfo = {
  app_name: 'BARSA',
  version: '0.1.0',
  environment: 'development',
  storage_provider: 'sqlite',
  falkordb_status: 'connected' as const,
  active_workspaces: 1,
  total_projects: 1,
};

function renderWithProviders(ui: React.ReactElement, initialRoute = '/') {
  return render(
    <AppProvider>
      <MemoryRouter initialEntries={[initialRoute]}>{ui}</MemoryRouter>
    </AppProvider>
  );
}

describe('BARSA Web Dashboard Comprehensive Test Suite', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getInfo').mockResolvedValue(mockSystemInfo);
    vi.spyOn(api, 'getCurrentPrincipal').mockResolvedValue(mockPrincipal);
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue([mockWorkspace]);
    vi.spyOn(api, 'listProjects').mockResolvedValue([mockProject]);
    vi.spyOn(api, 'getProject').mockResolvedValue(mockProject);
    vi.spyOn(api, 'listRecords').mockResolvedValue([mockRecord]);
    vi.spyOn(api, 'listCommits').mockResolvedValue([mockCommit]);
    vi.spyOn(api, 'listBranches').mockResolvedValue([mockBranch]);
    vi.spyOn(api, 'listReviews').mockResolvedValue([]);
    vi.spyOn(api, 'listConflicts').mockResolvedValue([]);
    vi.spyOn(api, 'listAgents').mockResolvedValue([mockAgent]);
    vi.spyOn(api, 'listTasks').mockResolvedValue([mockTask]);
    vi.spyOn(api, 'getGraphOverview').mockResolvedValue(mockGraphOverview);
    vi.spyOn(api, 'getSubgraph').mockResolvedValue(mockSubgraph);
    vi.spyOn(api, 'listArtifacts').mockResolvedValue([]);
    vi.spyOn(api, 'listAuditEvents').mockResolvedValue([]);
  });

  // 1. Dashboard rendering
  it('1. renders dashboard home with system overview cards and metrics', async () => {
    renderWithProviders(<DashboardHome />);
    expect(await screen.findByText('System Overview')).toBeInTheDocument();
    expect(screen.getByText('Connected Agents')).toBeInTheDocument();
    expect(screen.getByText('Version Commits')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
  });

  // 2. Workspace list
  it('2. displays workspaces list correctly', async () => {
    renderWithProviders(<WorkspacesPage />);
    expect(await screen.findByText('Engineering Workspace')).toBeInTheDocument();
    expect(screen.getByText(/Core Engineering team memory/)).toBeInTheDocument();
  });

  // 3. Project creation
  it('3. opens project creation modal and submits new project', async () => {
    const createProjectSpy = vi.spyOn(api, 'createProject').mockResolvedValue({
      project_id: 'proj_new_2',
      workspace_id: 'ws_eng_1',
      name: 'Agent Memory Sync',
      status: 'active',
      created_at: '2026-10-14T14:00:00Z',
      updated_at: '2026-10-14T14:00:00Z',
    });

    renderWithProviders(<ProjectsPage />);
    const newBtn = await screen.findByRole('button', { name: /New Project/i });
    fireEvent.click(newBtn);

    const input = screen.getByLabelText(/Project Name/i);
    fireEvent.change(input, { target: { value: 'Agent Memory Sync' } });

    const submitBtn = screen.getByRole('button', { name: /Create Project/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createProjectSpy).toHaveBeenCalledWith('ws_eng_1', {
        name: 'Agent Memory Sync',
        description: undefined,
      });
    });
  });

  // 4. Project details
  it('4. displays project detail page with status and commits', async () => {
    render(
      <AppProvider>
        <MemoryRouter initialEntries={['/projects/proj_api_1']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AppProvider>
    );

    expect(await screen.findByText('API Redesign')).toBeInTheDocument();
    expect(screen.getByText('FastAPI memory backend overhaul')).toBeInTheDocument();
    expect(screen.getByText('Latest Approved Commit')).toBeInTheDocument();
  });

  // 5. Memory search
  it('5. searches memory records by title and query filter', async () => {
    renderWithProviders(<MemoryExplorerPage />);
    expect(await screen.findByText('SQLite Local Engine Adoption')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/Search records by title/i);
    fireEvent.change(searchInput, { target: { value: 'Nonexistent Record' } });

    expect(screen.queryByText('SQLite Local Engine Adoption')).not.toBeInTheDocument();
    expect(screen.getByText(/No records match your search/i)).toBeInTheDocument();
  });

  // 6. Memory record inspection
  it('6. inspects memory record details upon clicking', async () => {
    renderWithProviders(<MemoryExplorerPage />);
    const card = await screen.findByText('SQLite Local Engine Adoption');
    fireEvent.click(card);

    expect(screen.getByText(/Comprehensive ADR details regarding SQLite WAL mode/)).toBeInTheDocument();
    expect(screen.getByText('rec_bms_100')).toBeInTheDocument();
  });

  // 7. Commit history
  it('7. displays commit history list and author information', async () => {
    renderWithProviders(<VersionControlPage />);
    expect(await screen.findByText('feat: add initial SQLite schema')).toBeInTheDocument();
    expect(screen.getByText(/Author: Alice Agent/)).toBeInTheDocument();
  });

  // 8. Diff visualization
  it('8. visualizes structured diffs for selected commits', async () => {
    vi.spyOn(api, 'getDiff').mockResolvedValue({
      base_commit_hash: 'root',
      target_commit_hash: 'a1b2c3d4e5f6',
      changed_records: {
        rec_bms_100: {
          operation: 'create',
          fields: {
            title: { old: null, new: 'SQLite Local Engine Adoption' },
          },
        },
      },
    });

    renderWithProviders(<VersionControlPage />);
    const commitCard = await screen.findByText('feat: add initial SQLite schema');
    fireEvent.click(commitCard);

    expect(await screen.findByText('Structured Diff Against Parent')).toBeInTheDocument();
  });

  // 9. Conflict display
  it('9. displays merge conflicts with base, source, and target values', async () => {
    vi.spyOn(api, 'listConflicts').mockResolvedValue([
      {
        record_id: 'rec_bms_100',
        field_name: 'summary',
        base_value: 'Initial value',
        source_value: 'Branch A value',
        target_value: 'Main value',
        is_resolved: false,
      },
    ]);

    renderWithProviders(<VersionControlPage />);
    const conflictsTab = await screen.findByRole('button', { name: /Conflicts/i });
    fireEvent.click(conflictsTab);

    expect(await screen.findByText(/Conflict in rec_bms_100/i)).toBeInTheDocument();
    expect(screen.getByText('Base Value')).toBeInTheDocument();
    expect(screen.getByText('Source (Branch)')).toBeInTheDocument();
    expect(screen.getByText('Target (Main)')).toBeInTheDocument();
  });

  // 10. Review actions
  it('10. switches to reviews tab and shows review status', async () => {
    vi.spyOn(api, 'listReviews').mockResolvedValue([
      {
        review_id: 'rev_1',
        project_id: 'proj_api_1',
        source_branch: 'feature-bms',
        target_branch: 'main',
        title: 'Review BMS schema update',
        status: 'pending',
        author_id: 'agent_bob',
        created_at: '2026-10-14T12:00:00Z',
        comments: [],
      },
    ]);

    renderWithProviders(<VersionControlPage />);
    const reviewsTab = await screen.findByRole('button', { name: /Reviews/i });
    fireEvent.click(reviewsTab);

    expect(await screen.findByText('Review BMS schema update')).toBeInTheDocument();
    expect(screen.getByText(/feature-bms → main/)).toBeInTheDocument();
  });

  // 11. Graph navigation
  it('11. renders knowledge graph nodes and inspects node selection', async () => {
    renderWithProviders(<GraphExplorerPage />);
    expect(await screen.findByText(/FalkorDB Knowledge Graph/i)).toBeInTheDocument();

    // Switch to table mode for semantic accessibility check
    const tableBtn = screen.getByRole('button', { name: /Accessible Table/i });
    fireEvent.click(tableBtn);

    expect(await screen.findByText('Accessible Graph Entity List')).toBeInTheDocument();
    expect(screen.getByText('SQLite Decision')).toBeInTheDocument();
  });

  // 12. Graph unavailable state
  it('12. displays graceful notification when FalkorDB is inactive', async () => {
    vi.spyOn(api, 'getInfo').mockResolvedValue({
      ...mockSystemInfo,
      falkordb_status: 'disabled',
    });

    renderWithProviders(<GraphExplorerPage />);
    expect(await screen.findByText('FalkorDB Disabled / Inactive')).toBeInTheDocument();
  });

  // 13. Agent registry
  it('13. displays registered agent capabilities and workloads', async () => {
    renderWithProviders(<AgentsPage />);
    expect(await screen.findByText('QA Copilot')).toBeInTheDocument();
    expect(screen.getByText(/Provider:/)).toBeInTheDocument();
    expect(screen.getByText('1 active tasks')).toBeInTheDocument();
  });

  // 14. Task board
  it('14. displays coordination tasks across status columns', async () => {
    renderWithProviders(<TasksPage />);
    expect(await screen.findByText('Audit credential rotation endpoints')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  // 15. Checkpoint retrieval & 16. Context package generation
  it('15 & 16. generates and displays context resume package from Smart Context Engine', async () => {
    const resumeSpy = vi.spyOn(api, 'resumeContext').mockResolvedValue({
      package_id: 'pkg_res_1',
      project_id: 'proj_api_1',
      created_at: '2026-10-14T14:30:00Z',
      token_budget: 8000,
      total_tokens: 340,
      counting_method: 'cl100k_base',
      records_included: 2,
      records_omitted: 0,
      summary_text: 'Resume summary for API Redesign',
      rendered_context: '# BARSA PROJECT CONTEXT\nProject: API Redesign\nVerified records: 2',
      records: [mockRecord],
    });

    render(
      <AppProvider>
        <MemoryRouter initialEntries={['/projects/proj_api_1']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AppProvider>
    );

    const resumeBtn = await screen.findByRole('button', { name: /Resume Context/i });
    fireEvent.click(resumeBtn);

    await waitFor(() => {
      expect(resumeSpy).toHaveBeenCalledWith('proj_api_1', 8000);
    });

    expect(await screen.findByText(/Optimized Resume Context Package/i)).toBeInTheDocument();
    expect(screen.getByText(/340 tokens/)).toBeInTheDocument();
  });

  // 17. Permission-aware UI
  it('17. displays current authenticated identity and superuser clearance badge', async () => {
    renderWithProviders(<SecurityPage />);
    expect(await screen.findByText('Current Authenticated Principal')).toBeInTheDocument();
    expect(screen.getByText('Local Desktop Owner')).toBeInTheDocument();
    expect(screen.getByText('SUPERUSER')).toBeInTheDocument();
  });

  // 18. Credential generation & one-time display
  it('18. displays newly issued agent API key secret only once with warning', async () => {
    vi.spyOn(api, 'createAgentCredential').mockResolvedValue({
      credential_id: 'cred_99',
      raw_key: 'barsa_ak_deadbeefcafebabefeed',
    });

    renderWithProviders(<SecurityPage />);
    const issueBtn = await screen.findByRole('button', { name: /Issue Agent API Key/i });
    fireEvent.click(issueBtn);

    const idInput = screen.getByPlaceholderText(/agt_claude_reviewer/i);
    fireEvent.change(idInput, { target: { value: 'agt_new' } });

    const submitBtn = screen.getByRole('button', { name: /Generate Key/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/One-Time Secret Key Display/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('barsa_ak_deadbeefcafebabefeed')).toBeInTheDocument();
  });

  // 19. Package import & 20. Package export
  it('19 & 20. supports BMS portable package import modal and export trigger', async () => {
    const exportSpy = vi.spyOn(api, 'exportProject').mockResolvedValue({
      schema_version: '0.1.0',
      project: mockProject,
      records: [mockRecord],
    });

    renderWithProviders(<StoragePage />);
    const exportBtn = await screen.findByRole('button', { name: /Export Project Memory/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(exportSpy).toHaveBeenCalledWith('proj_api_1');
    });

    const importBtn = screen.getByRole('button', { name: /Import BMS Package/i });
    fireEvent.click(importBtn);

    expect(await screen.findByText(/Upload JSON Package File/i)).toBeInTheDocument();
  });

  // 21. API error handling & 22. Unauthorized responses
  it('21 & 22. handles API errors gracefully without crashing the UI', async () => {
    vi.spyOn(api, 'listRecords').mockRejectedValue(new ApiError(403, 'Permission denied on restricted records'));

    renderWithProviders(<MemoryExplorerPage />);
    // Should display empty or fallback state instead of throwing unhandled exception
    expect(await screen.findByText('Memory Explorer')).toBeInTheDocument();
  });

  // 23. Responsive navigation
  it('23. renders responsive sidebar navigation links', async () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('Workspaces')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Memory Explorer')).toBeInTheDocument();
    expect(screen.getByText('Version Control')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
  });

  // 24. Keyboard accessibility
  it('24. supports accessible dialog dismissal via keyboard Escape key', async () => {
    renderWithProviders(<WorkspacesPage />);
    const newWsBtn = await screen.findByRole('button', { name: /New Workspace/i });
    fireEvent.click(newWsBtn);

    expect(screen.getByRole('heading', { name: 'Create Workspace' })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByText('A workspace provides a security boundary for AI agent memory.')).not.toBeInTheDocument();
    });
  });
});
