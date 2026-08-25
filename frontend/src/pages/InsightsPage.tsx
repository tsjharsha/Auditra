import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FlaskConical, ShieldAlert, TrendingUp } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { Field, Input, Select } from "../components/ui/Field";
import { Tabs } from "../components/ui/Tabs";
import { EmptyState } from "../components/ui/State";
import { compact, money, ms, pct, titleCase } from "../lib/format";
import { attentionCases, potentialExposure } from "../lib/product";
import { statusTone } from "../lib/status";
import { useAuditra, type ControlledEvaluationSettings } from "../hooks/useAuditra";
import type { AnomalyMode, FailureRecord, ReconciliationCase } from "../types/auditra";

type InsightTab = "overview" | "baseline" | "failures" | "performance";

const initialRates: Record<string, string> = {
  AMOUNT_MISMATCH: "0.0400",
  MISSING_SETTLEMENT: "0.0300",
  DUPLICATE_PAYMENT: "0.0200",
  FEE_MISMATCH: "0.0200",
  REFUND_MISMATCH: "0.0200",
  PARTIAL_SETTLEMENT: "0.0300",
  TIMING_MISMATCH: "0.0200",
  CONFLICTING_EVIDENCE: "0.0200",
  CURRENCY_MISMATCH: "0.0100",
  ENTITY_LINK_FAILURE: "0.0100",
};

export function InsightsPage() {
  const { audit, comparison, runComparison, breakController, runControlledEvaluation, selectCase, runHistory, isBusy } = useAuditra();
  const [tab, setTab] = useState<InsightTab>("overview");
  const [settings, setSettings] = useState<ControlledEvaluationSettings>({
    recordCount: 500,
    seed: 91,
    anomalyMode: "STRESSED",
    anomalyRates: initialRates,
  });

  if (!audit) {
    return <EmptyState title="No insights yet" detail="Run an audit first. Auditra will turn the result into useful insights about exposure, quality, and review load." />;
  }

  const comparisonRows = comparison?.comparison ?? audit.comparison.comparison ?? [];
  const aiRow = comparisonRows.find((row) => row.mode === "ai_assisted");
  const baseRow = comparisonRows.find((row) => row.mode === "deterministic_only");
  const attention = attentionCases(audit);
  const exposure = potentialExposure(attention);
  const topIssue = attention[0];
  const exposureByStatus = Object.entries(
    attention.reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = (acc[item.status] ?? 0) + Number(item.decision.financial_impact ?? 0);
      return acc;
    }, {}),
  ).map(([status, value]) => ({
    status: titleCase(status),
    exposure: Number(value.toFixed(2)),
  }));
  const failureData = Object.entries(audit.evaluation.metrics.failure_taxonomy).map(([name, count]) => ({
    name: titleCase(name),
    count,
  }));

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-3">
        <SummaryTile
          title="Where problems are happening"
          value={topIssue ? caseInsight(topIssue.status) : "Healthy activity"}
          detail={topIssue ? `${money(topIssue.decision.financial_impact)} is the largest single exposure in the current audit.` : "Auditra did not surface a major exception category."}
        />
        <SummaryTile
          title="What needs attention"
          value={`${compact(attention.length)} cases`}
          detail={attention.length ? `${money(exposure)} of potential exposure is concentrated in the current queue.` : "No urgent review queue is open right now."}
        />
        <SummaryTile
          title="Controller value"
          value={aiRow && baseRow ? pct(aiRow.metrics.accuracy - baseRow.metrics.accuracy, 2) : pct(audit.evaluation.metrics.accuracy, 1)}
          detail={aiRow && baseRow ? "Accuracy lift versus the deterministic baseline on the same dataset." : "Run AI vs baseline to quantify the lift."}
        />
      </section>

      <Tabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "baseline", label: "AI vs Baseline" },
          { id: "failures", label: "Failures", count: audit.evaluation.failures.length },
          { id: "performance", label: "Performance" },
        ]}
        active={tab}
        onChange={(next) => setTab(next as InsightTab)}
      />

      {tab === "overview" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <ChartCard title="Where exposure is coming from" kicker="Financial exposure grouped by issue type">
            {exposureByStatus.length ? <ExposureChart data={exposureByStatus} /> : <EmptyState title="No exposure chart" detail="There are no active exception categories in this audit." />}
          </ChartCard>
          <ChartCard title="What failed most often" kicker="Failure categories surfaced by evaluation">
            {failureData.length ? <FailureChart data={failureData} /> : <EmptyState title="No failure analysis" detail="This evaluation did not produce a failure taxonomy." />}
          </ChartCard>
        </div>
      ) : null}

      {tab === "baseline" ? (
        <div className="space-y-4">
          <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
            <SectionHeader title="AI vs baseline" kicker="Compare Auditra's AI-assisted mode against the deterministic controller on the same dataset" action={<Button disabled={isBusy} onClick={() => void runComparison()}>Run comparison</Button>} />
            {comparisonRows.length ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {comparisonRows.map((row) => (
                  <div key={row.mode} className="rounded-[24px] border border-line bg-slate-50/80 p-5">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-lg font-semibold text-slate-950">{row.mode === "ai_assisted" ? "AI-assisted" : "Deterministic only"}</div>
                      <Badge tone={row.failures ? "warning" : "success"}>{row.failures} failures</Badge>
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <InsightMetric label="Accuracy" value={pct(row.metrics.accuracy)} />
                      <InsightMetric label="Precision" value={pct(row.metrics.precision)} />
                      <InsightMetric label="Recall" value={pct(row.metrics.recall)} />
                      <InsightMetric label="F1" value={pct(row.metrics.f1)} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No comparison yet" detail="Run the comparison to measure AI lift against the deterministic baseline." />
            )}
          </Card>
        </div>
      ) : null}

      {tab === "failures" ? (
        <div className="space-y-4">
          <ChartCard title="Failure taxonomy" kicker="Evaluation categories that most often produce incorrect outcomes">
            {failureData.length ? <FailureChart data={failureData} /> : <EmptyState title="No failure taxonomy" detail="The current evaluation run has no failure categories to display." />}
          </ChartCard>
          <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
            <SectionHeader title="Failure replay" kicker="Open any failed case to review the underlying transaction in context" />
            <DataTable rows={audit.evaluation.failures} columns={failureColumns(audit.controller_run.cases)} getRowId={(row) => row.case_id} onRowClick={(row) => selectCase(row.case_id)} emptyTitle="No failed cases" />
          </Card>
        </div>
      ) : null}

      {tab === "performance" ? (
        <div className="space-y-4">
          <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
            <SectionHeader title="Performance overview" kicker="A polished view of the metrics that matter for trust, speed, and cost" />
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <InsightMetric label="Accuracy" value={pct(audit.evaluation.metrics.accuracy)} />
              <InsightMetric label="Precision" value={pct(audit.evaluation.metrics.precision)} />
              <InsightMetric label="Recall" value={pct(audit.evaluation.metrics.recall)} />
              <InsightMetric label="F1" value={pct(audit.evaluation.metrics.f1)} />
              <InsightMetric label="Throughput" value={`${compact(audit.controller_run.metrics.throughput_records_per_sec)}/sec`} />
              <InsightMetric label="Median latency" value={ms(audit.controller_run.metrics.median_latency_ms)} />
              <InsightMetric label="P95 latency" value={ms(audit.controller_run.metrics.p95_latency_ms)} />
              <InsightMetric label="AI cost" value={`USD ${audit.evaluation.metrics.estimated_ai_cost_usd}`} />
            </div>
          </Card>

          <Card className="rounded-[32px] border-white/70 bg-[linear-gradient(135deg,rgba(79,70,229,0.08),rgba(255,255,255,0.94),rgba(14,165,233,0.06))] p-6">
            <SectionHeader title="Advanced testing" kicker="Test how Auditra behaves when financial data becomes difficult" />
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
              <div className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  {(["NORMAL", "STRESSED", "ADVERSARIAL"] as AnomalyMode[]).map((mode) => (
                    <Button key={mode} icon={<FlaskConical className="h-4 w-4" />} disabled={isBusy} onClick={() => void breakController(mode, settings.recordCount)}>
                      {titleCase(mode.toLowerCase())}
                    </Button>
                  ))}
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <Field label="Records">
                    <Input type="number" min={50} max={5000} value={settings.recordCount} onChange={(event) => setSettings({ ...settings, recordCount: Number(event.target.value) })} />
                  </Field>
                  <Field label="Seed">
                    <Input type="number" value={settings.seed} onChange={(event) => setSettings({ ...settings, seed: Number(event.target.value) })} />
                  </Field>
                  <Field label="Mode">
                    <Select value={settings.anomalyMode} onChange={(event) => setSettings({ ...settings, anomalyMode: event.target.value as AnomalyMode })}>
                      {["NORMAL", "STRESSED", "ADVERSARIAL", "CHAOS"].map((mode) => (
                        <option key={mode} value={mode}>
                          {mode}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <Button variant="primary" icon={<TrendingUp className="h-4 w-4" />} disabled={isBusy} onClick={() => void runControlledEvaluation(settings)}>
                  Run controlled evaluation
                </Button>
              </div>
              <div className="rounded-[28px] border border-white/80 bg-white/90 p-5">
                <div className="text-sm font-semibold text-slate-950">Session history</div>
                <div className="mt-4 space-y-3">
                  {runHistory.slice(0, 4).map((run) => (
                    <div key={run.runId} className="rounded-2xl border border-line bg-slate-50/80 p-3">
                      <div className="text-sm font-semibold text-slate-950">{run.mode}</div>
                      <div className="text-sm text-muted">{compact(run.records)} records</div>
                    </div>
                  ))}
                  {!runHistory.length ? <div className="text-sm text-muted">No controlled evaluations recorded in this session yet.</div> : null}
                </div>
              </div>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

function SummaryTile({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</div>
      <div className="mt-2 text-sm leading-6 text-muted">{detail}</div>
    </Card>
  );
}

function ChartCard({ title, kicker, children }: { title: string; kicker: string; children: React.ReactNode }) {
  return (
    <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
      <SectionHeader title={title} kicker={kicker} />
      <div className="h-[320px]">{children}</div>
    </Card>
  );
}

function InsightMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-slate-50/80 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function ExposureChart({ data }: { data: Array<{ status: string; exposure: number }> }) {
  return (
    <ResponsiveContainer>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="status" tickLine={false} axisLine={false} />
        <YAxis tickLine={false} axisLine={false} />
        <Tooltip formatter={(value) => money(Number(value))} />
        <Bar dataKey="exposure" fill="#4f46e5" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function FailureChart({ data }: { data: Array<{ name: string; count: number }> }) {
  return (
    <ResponsiveContainer>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={false} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
        <Tooltip />
        <Legend />
        <Bar dataKey="count" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function failureColumns(cases: ReconciliationCase[]): Column<FailureRecord>[] {
  return [
    {
      key: "case",
      header: "Case",
      value: (row) => titleCase(row.failure_category),
      sortValue: (row) => row.failure_category,
    },
    {
      key: "expected",
      header: "Expected",
      value: (row) => <Badge tone={statusTone(row.expected)}>{titleCase(row.expected)}</Badge>,
      sortValue: (row) => row.expected,
    },
    {
      key: "predicted",
      header: "Predicted",
      value: (row) => <Badge tone={statusTone(row.predicted)}>{titleCase(row.predicted)}</Badge>,
      sortValue: (row) => row.predicted,
    },
    {
      key: "impact",
      header: "Exposure",
      value: (row) => money(row.financial_impact),
      sortValue: (row) => Number(row.financial_impact),
    },
    {
      key: "evidence",
      header: "Evidence",
      value: (row) => cases.find((item) => item.case_id === row.case_id)?.evidence.length ?? row.evidence_available.length,
      sortValue: (row) => cases.find((item) => item.case_id === row.case_id)?.evidence.length ?? row.evidence_available.length,
    },
  ];
}

function caseInsight(status: string) {
  if (status === "MISSING_SETTLEMENT") return "Settlement gaps";
  if (status === "AMOUNT_MISMATCH") return "Amount mismatches";
  if (status === "HUMAN_REVIEW" || status === "UNRESOLVED") return "Escalated reviews";
  return titleCase(status);
}
