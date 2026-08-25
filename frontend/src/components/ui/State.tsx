import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";
import { Card } from "./Card";

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="flex min-h-40 flex-col justify-center">
      <div className="text-sm font-bold text-ink">{title}</div>
      {detail ? <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{detail}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </Card>
  );
}

export function LoadingState({ title = "Working", detail }: { title?: string; detail?: string }) {
  return (
    <Card className="flex items-center gap-3">
      <Loader2 className="h-5 w-5 animate-spin text-teal" />
      <div>
        <div className="text-sm font-bold text-ink">{title}</div>
        {detail ? <div className="text-sm text-muted">{detail}</div> : null}
      </div>
    </Card>
  );
}

export function ErrorState({ title = "Request failed", error, onRetry }: { title?: string; error?: unknown; onRetry?: () => void }) {
  return (
    <Card className="border-rose-200 bg-rose-50/80">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 text-rose" />
        <div className="min-w-0">
          <div className="text-sm font-bold text-rose">{title}</div>
          <p className="mt-1 break-words text-sm leading-6 text-rose/80">
            {error instanceof Error ? error.message : String(error ?? "Unknown error")}
          </p>
          {onRetry ? <Button className="mt-3" variant="danger" onClick={onRetry}>Retry</Button> : null}
        </div>
      </div>
    </Card>
  );
}

export function SuccessState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
      <div className="flex items-center gap-2 text-sm font-bold text-emerald-700">
        <CheckCircle2 className="h-4 w-4" />
        {title}
      </div>
      {detail ? <p className="mt-1 text-sm text-emerald-700/80">{detail}</p> : null}
    </div>
  );
}
