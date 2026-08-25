import { AlertTriangle, ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/State";
import { AuditProgress } from "../features/audit/AuditProgress";
import { compact, money, pct, titleCase } from "../lib/format";
import { attentionCases, auditHealthLabel, auditHealthRatio, auditHealthTone, caseShortExplanation, caseTitle, potentialExposure } from "../lib/product";
import { riskTone, statusTone } from "../lib/status";
import { useAuditra } from "../hooks/useAuditra";
import type { ReconciliationCase } from "../types/auditra";

export function AuditsPage() {
  const { audit, world, isBusy, auditWorld, selectCase, setActivePage } = useAuditra();

  if (!audit) {
    return (
      <EmptyState
        title="No audit yet"
        detail={world ? "Your world is ready. Start the audit to see what happened, what matters, and what needs review." : "Build a financial world first, then Auditra can audit it for you."}
        action={
          world ? (
            <Button variant="primary" icon={<ShieldCheck className="h-4 w-4" />} disabled={isBusy} onClick={() => void auditWorld()}>
              Audit this world
            </Button>
          ) : (
            <Button variant="primary" onClick={() => setActivePage("worlds")}>Create a world</Button>
          )
        }
      />
    );
  }

  const cases = attentionCases(audit);
  const health = auditHealthRatio(audit);
  const exposure = potentialExposure(cases);

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_360px]">
        <Card className="rounded-[32px] border-white/70 bg-[linear-gradient(135deg,rgba(34,197,94,0.08),rgba(79,70,229,0.10),rgba(255,255,255,0.96))] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <Badge tone={auditHealthTone(audit)}>{auditHealthLabel(audit)}</Badge>
              <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">Audit complete</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Auditra finished reconciling this financial world and highlighted the activity that needs your attention.
              </p>
            </div>
            <Button onClick={() => setActivePage("insights")}>Open insights</Button>
          </div>

          <div className="mt-8 rounded-[28px] border border-white/80 bg-white/92 p-6">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Audit health</div>
            <div className="mt-3 text-5xl font-semibold tracking-tight text-slate-950">{pct(health, 1)}</div>
            <div className="mt-2 text-base font-medium text-slate-700">{auditHealthLabel(audit)} financial activity</div>
            <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,#22c55e_0%,#38bdf8_60%,#4f46e5_100%)]"
                style={{ width: `${Math.max(8, Math.min(100, health * 100))}%` }}
              />
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <MetricLike label="Transactions checked" value={compact(audit.controller_run.metrics.transactions_processed)} />
              <MetricLike label="Need attention" value={compact(cases.length)} />
              <MetricLike label="Potential exposure" value={money(exposure)} />
            </div>
          </div>
        </Card>

        <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
          <SectionHeader title="What happened" kicker="A concise read on the current audit" />
          <div className="space-y-3">
            <InsightRow label="Matched automatically" value={pct(audit.controller_run.metrics.automatic_resolution_rate)} tone="success" />
            <InsightRow label="Needs review" value={pct(audit.controller_run.metrics.human_review_rate)} tone="review" />
            <InsightRow label="Unresolved" value={pct(audit.controller_run.metrics.unresolved_rate)} tone={audit.controller_run.metrics.unresolved_rate > 0 ? "warning" : "success"} />
            <InsightRow label="Controller accuracy" value={pct(audit.evaluation.metrics.accuracy)} tone="success" />
          </div>
        </Card>
      </section>

      <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
        <SectionHeader title="Needs your attention" kicker={cases.length ? "Start with the most important exceptions." : "No urgent exceptions were found."} />
        {cases.length ? (
          <div className="grid gap-4 xl:grid-cols-3">
            {cases.slice(0, 5).map((item) => (
              <button
                key={item.case_id}
                className="rounded-[28px] border border-line bg-slate-50/80 p-5 text-left transition hover:-translate-y-0.5 hover:bg-white"
                onClick={() => {
                  selectCase(item.case_id);
                  setActivePage("review");
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className={`grid h-10 w-10 place-items-center rounded-2xl ${item.status === "MISSING_SETTLEMENT" || item.status === "AMOUNT_MISMATCH" ? "bg-rose-50 text-rose-600" : "bg-amber-50 text-amber-600"}`}>
                      {item.status === "MISSING_SETTLEMENT" || item.status === "AMOUNT_MISMATCH" ? <AlertTriangle className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-slate-950">{caseTitle(item)}</div>
                      <div className="text-sm text-muted">{money(item.decision.financial_impact)} exposure</div>
                    </div>
                  </div>
                  <Badge tone={riskTone(item.risk_score)}>Risk {item.risk_score.toFixed(1)}</Badge>
                </div>
                <p className="mt-4 text-sm leading-6 text-muted">{caseShortExplanation(item)}</p>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Badge tone={statusTone(item.status)}>{titleCase(item.status)}</Badge>
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700">
                    Review
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="rounded-[28px] border border-emerald-200 bg-emerald-50/80 p-5">
            <div className="flex items-center gap-2 text-emerald-900">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-semibold">This audit is in a healthy state.</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-emerald-800">Auditra did not surface urgent exceptions. Open Insights if you want a deeper look at accuracy, AI value, and failure analysis.</p>
          </div>
        )}
      </Card>

      <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
        <SectionHeader title="Audit flow" kicker="A simple view of the work Auditra completed" />
        <AuditProgress audit={audit} running={isBusy} />
      </Card>

      <details className="rounded-[32px] border border-white/70 bg-white/90 p-6 shadow-panel">
        <summary className="cursor-pointer text-sm font-semibold text-slate-950">View all cases</summary>
        <div className="mt-5">
          <DataTable rows={audit.controller_run.cases} columns={caseColumns} getRowId={(row) => row.case_id} onRowClick={(row) => selectCase(row.case_id)} />
        </div>
      </details>
    </div>
  );
}

function MetricLike({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-slate-50/80 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-semibold tracking-tight text-slate-950">{value}</div>
    </div>
  );
}

function InsightRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "success" | "warning" | "review";
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-line bg-slate-50/80 px-4 py-3">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <Badge tone={tone}>{value}</Badge>
    </div>
  );
}

const caseColumns: Column<ReconciliationCase>[] = [
  {
    key: "case",
    header: "Case",
    value: (row) => caseTitle(row),
    sortValue: (row) => row.status,
  },
  {
    key: "payment",
    header: "Payment",
    value: (row) => row.payment_id,
    sortValue: (row) => row.payment_id,
    className: "font-mono text-xs",
  },
  {
    key: "status",
    header: "Status",
    value: (row) => <Badge tone={statusTone(row.status)}>{titleCase(row.status)}</Badge>,
    sortValue: (row) => row.status,
  },
  {
    key: "impact",
    header: "Exposure",
    value: (row) => money(row.decision.financial_impact),
    sortValue: (row) => Number(row.decision.financial_impact),
  },
  {
    key: "risk",
    header: "Risk",
    value: (row) => <Badge tone={riskTone(row.risk_score)}>Risk {row.risk_score.toFixed(1)}</Badge>,
    sortValue: (row) => row.risk_score,
  },
];
