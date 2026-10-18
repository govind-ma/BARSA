import { useState } from 'react';
import { useApp } from '@/app/AppContext';
import { NewProjectModal } from '@/components/projects/NewProjectModal';
import { Sparkles, Plus, ArrowRight, FileCode } from 'lucide-react';

export function ProjectOnboarding() {
  const { projects, setActiveProjectId, setActiveWorkspaceId } = useApp();
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);

  // Take first 3 projects as cards
  const topProjects = projects.slice(0, 3);

  return (
    <div className="min-h-[75vh] flex flex-col items-center justify-center max-w-4xl mx-auto px-4 py-8 animate-page-enter">
      {/* Hero Badge */}
      <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-ice/10 border border-ice/30 text-ice text-xs font-mono font-medium mb-4 shadow-[0_0_15px_rgba(56,189,248,0.2)]">
        <Sparkles className="h-3.5 w-3.5" />
        <span>Universal AI Memory Infrastructure</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight text-center mb-3">
        Pick a project to begin
      </h1>
      <p className="text-sm text-muted-foreground text-center max-w-md mb-8">
        Select an active workspace project to inspect its FalkorDB graph, track AI agent checkpoints, or start a new coordination session.
      </p>

      {/* 3 Project Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mb-8">
        {topProjects.map((proj) => (
          <div
            key={proj.project_id}
            onClick={() => {
              setActiveProjectId(proj.project_id);
              if (proj.workspace_id) setActiveWorkspaceId(proj.workspace_id);
            }}
            className="group relative flex flex-col justify-between p-5 rounded-2xl bg-card/80 hover:bg-card border border-ice/20 hover:border-ice/50 transition-all duration-200 cursor-pointer shadow-[0_8px_30px_rgba(0,0,0,0.3)] hover:shadow-[0_12px_40px_rgba(56,189,248,0.15)] active:scale-[0.98]"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="h-9 w-9 rounded-xl bg-ice/15 border border-ice/30 flex items-center justify-center text-ice group-hover:scale-105 transition-transform">
                  <FileCode className="h-4 w-4" />
                </div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-secondary border border-ice/15 text-muted-foreground group-hover:text-ice transition-colors">
                  {proj.status || 'Active'}
                </span>
              </div>

              <h3 className="text-sm font-bold text-foreground group-hover:text-ice transition-colors line-clamp-1 mb-1.5">
                {proj.name}
              </h3>
              <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                {proj.description || 'Autonomous multi-agent memory and graph-reasoning project.'}
              </p>
            </div>

            <div className="pt-4 mt-4 border-t border-ice/10 flex items-center justify-between text-xs text-muted-foreground group-hover:text-foreground">
              <span className="font-mono text-[11px] truncate max-w-[120px]">{proj.project_id}</span>
              <ArrowRight className="h-4 w-4 text-ice transform translate-x-0 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        ))}

        {/* Create Project Quick Card if less than 3 */}
        {topProjects.length < 3 && (
          <div
            onClick={() => setIsNewProjectOpen(true)}
            className="flex flex-col items-center justify-center p-6 rounded-2xl border-2 border-dashed border-ice/25 hover:border-ice/50 bg-secondary/20 hover:bg-secondary/40 transition-all cursor-pointer group text-center"
          >
            <div className="h-10 w-10 rounded-full bg-chilli/20 text-chilli flex items-center justify-center mb-2 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(239,68,68,0.3)]">
              <Plus className="h-5 w-5" />
            </div>
            <span className="text-xs font-bold text-foreground group-hover:text-chilli transition-colors">
              + New Project
            </span>
            <span className="text-[11px] text-muted-foreground mt-0.5">Initialize a new memory branch</span>
          </div>
        )}
      </div>

      {/* Or Create New Project Button */}
      <div className="flex items-center space-x-3">
        <button
          onClick={() => setIsNewProjectOpen(true)}
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-chilli hover:bg-chilli-hover active:scale-[0.98] transition-all shadow-[0_0_20px_rgba(239,68,68,0.4)]"
        >
          <Plus className="h-4 w-4" />
          <span>Create New Project</span>
        </button>
      </div>

      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
      />
    </div>
  );
}
