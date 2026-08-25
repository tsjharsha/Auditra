import { CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { jsonPreview, ms } from "../../lib/format";
import type { AgentToolCall } from "../../types/auditra";

export function ToolTrace({ calls }: { calls: AgentToolCall[] }) {
  if (!calls.length) {
    return <div className="rounded-lg border border-line bg-slate-50 p-3 text-sm text-muted">No tool calls were needed.</div>;
  }
  return (
    <div className="space-y-2">
      {calls.map((call) => (
        <details key={call.call_id} className="rounded-lg border border-line bg-white p-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-2 text-sm font-bold text-ink">
              {call.success ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-rose" />}
              <span className="truncate">{call.tool_name}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2">
              <Badge tone={call.success ? "success" : "danger"}>{call.success ? "ok" : call.error_type ?? "failed"}</Badge>
              <span className="text-xs text-muted">{ms(call.duration_ms)}</span>
            </span>
          </summary>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <pre className="overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
              {jsonPreview(call.input, 900)}
            </pre>
            <pre className="overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
              {jsonPreview(call.output, 900)}
            </pre>
          </div>
        </details>
      ))}
    </div>
  );
}
