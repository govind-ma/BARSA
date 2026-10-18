import { Component, ErrorInfo, ReactNode } from 'react';
import { BarsaLogo } from './BarsaLogo';
import { RotateCw, AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[BARSA Uncaught Exception Caught by ErrorBoundary]:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-bg-base text-text-primary flex items-center justify-center p-6 select-none animate-in fade-in">
          <div className="max-w-md w-full glass-card p-6 space-y-5 border border-border-strong shadow-2xl text-center">
            <div className="flex justify-center">
              <div className="relative">
                <BarsaLogo size={52} />
                <span className="absolute -bottom-1 -right-1 p-1 rounded-full bg-lava-red text-white shadow-md">
                  <AlertTriangle className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>

            <div className="space-y-1.5">
              <h2 className="font-heading font-semibold text-lg text-text-primary tracking-tight">
                Dashboard State Interruption
              </h2>
              <p className="text-xs text-text-secondary leading-relaxed">
                BARSA caught an unexpected UI rendering exception. Your underlying project memory and FalkorDB graph remain safe.
              </p>
            </div>

            {this.state.error && (
              <div className="p-3 rounded-lg bg-surface/80 border border-border-subtle text-left font-mono text-[11px] text-lava-red overflow-x-auto max-h-24">
                {this.state.error.message || String(this.state.error)}
              </div>
            )}

            <button
              onClick={this.handleReset}
              className="btn-magma w-full py-2.5 px-4 rounded-lg text-xs font-semibold text-white inline-flex items-center justify-center space-x-2 shadow-md active:scale-95"
            >
              <RotateCw className="w-3.5 h-3.5" />
              <span>Reload Mission Control</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
