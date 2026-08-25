import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Card } from "../../components/ui/Card";
import type { AuditWorldResult } from "../../types/auditra";

const stages = [
  "Understanding activity",
  "Reconciling payments",
  "Investigating exceptions",
  "Verifying results",
  "Preparing your report",
];

export function AuditProgress({ audit, running }: { audit?: AuditWorldResult | null; running: boolean }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      {stages.map((stage) => {
        const done = stageComplete(stage, audit);
        const active = running && !done;
        return (
          <Card key={stage} className={done ? "border-emerald-200 bg-emerald-50/70" : active ? "border-indigo-200 bg-indigo-50/70" : "bg-white/80"}>
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-bold text-ink">{stage}</div>
              {done ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : active ? <Loader2 className="h-4 w-4 animate-spin text-indigo" /> : <Circle className="h-4 w-4 text-muted" />}
            </div>
            <div className="mt-2 text-sm leading-6 text-muted">{stageDetail(stage)}</div>
            <div className="mt-3">
              <Badge tone={done ? "success" : active ? "review" : "muted"}>{done ? "complete" : active ? "running" : "waiting"}</Badge>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function stageComplete(stage: string, audit?: AuditWorldResult | null) {
  if (!audit) return false;
  const cases = audit.controller_run.cases;
  if (stage === "Understanding activity") return cases.some((item) => item.evidence.length > 0);
  if (stage === "Reconciling payments") return cases.length > 0;
  if (stage === "Investigating exceptions") return cases.some((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status));
  if (stage === "Verifying results") return cases.every((item) => item.decision.verification);
  if (stage === "Preparing your report") return Boolean(audit.evaluation.metrics);
  return false;
}

function stageDetail(stage: string) {
  if (stage === "Understanding activity") return "Mapping orders, payments, settlements, refunds and fees into a clean audit view.";
  if (stage === "Reconciling payments") return "Checking that captured activity lines up with expected financial outcomes.";
  if (stage === "Investigating exceptions") return "Focusing attention on the transactions that need explanation or review.";
  if (stage === "Verifying results") return "Cross-checking evidence so the final result can be trusted.";
  return "Packaging a concise summary of what happened, what matters and what to review next.";
}
