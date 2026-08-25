import { BookOpenCheck, PlayCircle } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { EmptyState } from "../components/ui/State";
import { jsonPreview, shortId } from "../lib/format";
import { useAuditra } from "../hooks/useAuditra";

export function AuditTrailPage() {
  const { audit, lastReviewEvent, runFiveMinuteDemo, isBusy } = useAuditra();
  const events = audit?.controller_run.audit_events ?? [];

  if (!audit) {
    return (
      <EmptyState
        title="No audit trail"
        detail="Audit a world to produce explainable controller events."
        action={<Button variant="primary" icon={<PlayCircle className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>Run 5-Minute Demo</Button>}
      />
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader title="Audit Trail" kicker={`${events.length} immutable-style events for ${audit.controller_run.run_id}`} />
        {lastReviewEvent ? (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
            {lastReviewEvent}
          </div>
        ) : null}
        <div className="space-y-3">
          {events.map((event) => (
            <div key={event.event_id} className="rounded-lg border border-line bg-white p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <BookOpenCheck className="h-4 w-4 text-teal" />
                  <span className="truncate text-sm font-black uppercase text-ink">{event.action}</span>
                  <Badge tone="muted">{event.actor}</Badge>
                </div>
                <span className="text-xs font-mono text-muted">{event.timestamp}</span>
              </div>
              <div className="mt-2 grid gap-2 text-sm text-muted md:grid-cols-3">
                <div>Entity: {event.entity}</div>
                <div>ID: {shortId(event.entity_id, 28)}</div>
                <div>Correlation: {shortId(event.correlation_id, 28)}</div>
              </div>
              <div className="mt-2 text-sm text-muted">{event.reason}</div>
              <details className="mt-3 rounded-lg border border-line bg-slate-50 p-3">
                <summary className="cursor-pointer text-sm font-bold text-ink">Inputs and Outputs</summary>
                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  <pre className="overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{jsonPreview(event.inputs_ref, 1200)}</pre>
                  <pre className="overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{jsonPreview(event.output_ref, 1200)}</pre>
                </div>
              </details>
            </div>
          ))}
          {!events.length ? <EmptyState title="No events recorded" detail="The controller run returned no audit events." /> : null}
        </div>
      </Card>
    </div>
  );
}
