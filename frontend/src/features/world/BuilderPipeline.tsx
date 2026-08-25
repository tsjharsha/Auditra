import { ArrowDown, CheckCircle2, Clock3, Loader2 } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Card } from "../../components/ui/Card";
import { cn } from "../../lib/utils";
import type { AuditWorldResult, WorldBuildResult, WorldPreview } from "../../types/auditra";

const stages = ["PROMPT", "UNDERSTAND", "STRUCTURE", "GENERATE", "VALIDATE"] as const;

export function BuilderPipeline({
  preview,
  world,
  audit,
  isBusy,
}: {
  preview?: WorldPreview | null;
  world?: WorldBuildResult | null;
  audit?: AuditWorldResult | null;
  isBusy: boolean;
}) {
  const state = {
    PROMPT: "complete",
    UNDERSTAND: preview ? "complete" : isBusy ? "active" : "waiting",
    STRUCTURE: preview?.schema_preview ? "complete" : isBusy ? "active" : "waiting",
    GENERATE: world ? "complete" : isBusy && preview ? "active" : "waiting",
    VALIDATE: world?.validation.valid ? "complete" : isBusy && world ? "active" : "waiting",
  } as const;

  const details = {
    PROMPT: preview?.spec.prompt ? "Prompt captured" : "Ready for financial intent",
    UNDERSTAND: preview ? `${preview.spec.record_count} orders, ${preview.spec.payment_methods.join(" / ")}` : "Parsed by backend",
    STRUCTURE: preview ? `${preview.schema_preview.entities.length} entities, ${preview.relationship_model.edges.length} relationships` : "Schema pending",
    GENERATE: world ? `${world.summary.payments} payments and ${world.summary.settlements} settlements` : "No generated ledger yet",
    VALIDATE: world ? `${world.validation.checks.length} checks, ${world.validation.valid ? "valid" : "needs attention"}` : "Validation pending",
  };

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
      {stages.map((stage, index) => (
        <div key={stage} className="relative">
          <Card
            className={cn(
              "h-full min-h-32",
              state[stage] === "complete" ? "border-emerald-200 bg-emerald-50/80" : "",
              state[stage] === "active" ? "border-indigo-200 bg-indigo-50/80" : "",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs font-black text-muted">{stage}</div>
              {state[stage] === "complete" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : null}
              {state[stage] === "active" ? <Loader2 className="h-4 w-4 animate-spin text-indigo" /> : null}
              {state[stage] === "waiting" ? <Clock3 className="h-4 w-4 text-muted" /> : null}
            </div>
            <div className="mt-4 text-sm font-semibold leading-6 text-ink">{details[stage]}</div>
            <div className="mt-3">
              <Badge tone={state[stage] === "complete" ? "success" : state[stage] === "active" ? "review" : "muted"}>
                {state[stage]}
              </Badge>
            </div>
          </Card>
          {index < stages.length - 1 ? (
            <ArrowDown className="absolute -bottom-3 left-1/2 z-10 hidden h-4 w-4 -translate-x-1/2 text-muted lg:-right-3 lg:left-auto lg:top-1/2 lg:block lg:-translate-y-1/2 lg:rotate-[-90deg]" />
          ) : null}
        </div>
      ))}
      {audit ? <div className="sr-only">{audit.survival_status}</div> : null}
    </div>
  );
}
