import { BarChart3, Gauge, Scale } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import { Metric, MetricGrid } from "../../components/ui/Metric";
import { EmptyState } from "../../components/ui/State";
import { money, ms, pct } from "../../lib/format";
import { statusTone } from "../../lib/status";
import type { AuditWorldResult, ControllerComparison } from "../../types/auditra";

export function ControllerDashboard({
  audit,
  comparison,
  onCompare,
  compareDisabled,
}: {
  audit?: AuditWorldResult | null;
  comparison?: ControllerComparison | null;
  onCompare: () => void;
  compareDisabled?: boolean;
}) {
  if (!audit) {
    return <EmptyState title="No controller run" detail="Audit a generated financial world to populate controller metrics." />;
  }

  const run = audit.controller_run;
  const evaluation = audit.evaluation.metrics;
  return (
    <div className="space-y-4">
      <MetricGrid>
        <Metric label="Records processed" value={run.metrics.transactions_processed} />
        <Metric label="Financial volume" value={money(run.metrics.total_payment_volume)} />
        <Metric label="Match rate" value={pct(run.metrics.match_rate)} tone="success" />
        <Metric label="Accuracy" value={pct(evaluation.accuracy)} tone="success" />
        <Metric label="Precision" value={pct(evaluation.precision)} />
        <Metric label="Recall" value={pct(evaluation.recall)} />
        <Metric label="F1" value={pct(evaluation.f1)} />
        <Metric label="Auto-resolution" value={pct(run.metrics.automatic_resolution_rate)} tone="success" />
        <Metric label="Human review" value={pct(run.metrics.human_review_rate)} tone={run.metrics.human_review_rate > 0 ? "review" : "success"} />
        <Metric label="Unresolved" value={pct(run.metrics.unresolved_rate)} tone={run.metrics.unresolved_rate > 0 ? "danger" : "success"} />
        <Metric label="Throughput" value={`${run.metrics.throughput_records_per_sec}/sec`} />
        <Metric label="P95 latency" value={ms(run.metrics.p95_latency_ms)} />
        <Metric label="AI invocation" value={pct(run.metrics.ai_invocation_rate)} detail={`${run.metrics.ai_investigation_count} cases`} tone="review" />
        <Metric label="AI cost" value={`USD ${run.metrics.estimated_ai_cost_usd}`} />
        <Metric label="Error impact" value={money(evaluation.financial_impact_of_errors)} tone={Number(evaluation.financial_impact_of_errors) > 0 ? "warning" : "success"} />
        <Metric label="Survival" value={audit.evaluation.failures.length ? "FAILED" : "SURVIVED"} tone={audit.evaluation.failures.length ? "warning" : "success"} />
      </MetricGrid>
      <Card>
        <SectionHeader
          title="AI vs Baseline"
          kicker="Same dataset, deterministic-only and AI-assisted modes"
          action={<Button icon={<Scale className="h-4 w-4" />} disabled={compareDisabled} onClick={onCompare}>Run Comparison</Button>}
        />
        <div className="grid gap-3 lg:grid-cols-2">
          {(comparison?.comparison ?? audit.comparison.comparison).map((row) => (
            <div key={row.mode} className="rounded-lg border border-line bg-slate-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-black uppercase text-ink">
                  {row.mode === "ai_assisted" ? <BarChart3 className="h-4 w-4 text-indigo" /> : <Gauge className="h-4 w-4 text-muted" />}
                  {row.mode.replace("_", " ")}
                </div>
                <Badge tone={statusTone(row.failures ? "PARTIAL_MATCH" : "MATCHED")}>{row.failures} failures</Badge>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div>Accuracy {pct(row.metrics.accuracy)}</div>
                <div>F1 {pct(row.metrics.f1)}</div>
                <div>Human review {pct(row.metrics.escalation_rate)}</div>
                <div>Latency {ms(row.metrics.p95_latency_ms)}</div>
                <div>Cost USD {row.metrics.estimated_ai_cost_usd}</div>
                <div>AI calls {row.metrics.llm_calls}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
