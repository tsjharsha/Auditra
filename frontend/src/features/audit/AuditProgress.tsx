import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Card } from "../../components/ui/Card";
import type { AuditWorldResult } from "../../types/auditra";

const stages = [
  "Entity resolution",
  "Graph construction",
  "Deterministic reconciliation",
  "Exception detection",
  "AI investigation",
  "Verification",
  "Evaluation",
];

export function AuditProgress({ audit, running }: { audit?: AuditWorldResult | null; running: boolean }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
      {stages.map((stage) => {
        const done = stageComplete(stage, audit);
        const active = running && !done;
        return (
          <Card key={stage} className={done ? "border-emerald-200 bg-emerald-50/70" : active ? "border-indigo-200 bg-indigo-50/70" : ""}>
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-bold text-ink">{stage}</div>
              {done ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : active ? <Loader2 className="h-4 w-4 animate-spin text-indigo" /> : <Circle className="h-4 w-4 text-muted" />}
            </div>
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
  if (stage === "Entity resolution") return cases.some((item) => item.evidence.length > 0);
  if (stage === "Graph construction") return cases.some((item) => item.graph.nodes.length > 0);
  if (stage === "Deterministic reconciliation") return cases.length > 0;
  if (stage === "Exception detection") return cases.some((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status));
  if (stage === "AI investigation") return audit.controller_run.metrics.ai_investigation_count >= 0;
  if (stage === "Verification") return cases.every((item) => item.decision.verification);
  if (stage === "Evaluation") return Boolean(audit.evaluation.metrics);
  return false;
}
