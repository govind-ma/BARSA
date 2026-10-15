import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FileQuestion, ArrowLeft } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh] animate-in fade-in">
      <Card className="max-w-md w-full text-center p-8 border-border/80 shadow-sm">
        <CardContent className="space-y-5 pt-4">
          <div className="inline-flex p-3 rounded-2xl bg-primary/10 text-primary">
            <FileQuestion className="h-10 w-10" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">404 Error</span>
            <h1 className="text-2xl font-bold tracking-tight text-foreground mt-1">Page Not Found</h1>
            <p className="text-sm text-muted-foreground mt-2">
              The page you are looking for doesn't exist, has been deleted, or has been moved to another location.
            </p>
          </div>
          <div className="pt-2">
            <Link to="/">
              <Button size="sm">
                <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
                Back to Overview
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
