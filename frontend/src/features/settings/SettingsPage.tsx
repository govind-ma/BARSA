import { useApp } from '@/app/AppContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Sun, Moon, Laptop, Terminal } from 'lucide-react';

export function SettingsPage() {
  const { theme, toggleTheme, systemInfo } = useApp();

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="border-b border-border pb-5">
        <h1 className="text-2xl font-bold tracking-tight">System Settings & Preferences</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Appearance, local daemon configuration, and developer environment info.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Appearance Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold flex items-center">
              <Laptop className="h-4 w-4 mr-2 text-primary" />
              Theme & Appearance
            </CardTitle>
            <CardDescription>Toggle between developer dark and accessible light mode</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-foreground block">Interface Theme</span>
                <span className="text-xs text-muted-foreground">Currently using {theme} mode</span>
              </div>
              <Button variant="outline" size="sm" onClick={toggleTheme} className="flex items-center">
                {theme === 'dark' ? <Sun className="h-4 w-4 mr-1.5" /> : <Moon className="h-4 w-4 mr-1.5 text-indigo-400" />}
                Switch to {theme === 'dark' ? 'Light' : 'Dark'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Runtime Environment */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold flex items-center">
              <Terminal className="h-4 w-4 mr-2 text-emerald-400" />
              Local Engine Environment
            </CardTitle>
            <CardDescription>Backend daemon configuration and service connections</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">App Name:</span>
              <span className="font-medium text-foreground">{systemInfo?.app_name || 'BARSA'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Core Version:</span>
              <span className="font-mono">{systemInfo?.version || '0.1.0'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Environment:</span>
              <Badge variant="outline" className="text-[10px] uppercase">
                {systemInfo?.environment || 'development'}
              </Badge>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Loopback Binding:</span>
              <span className="font-mono text-[11px]">127.0.0.1:8000</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
