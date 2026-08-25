import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FlaskConical, Scale } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { Field, Input, Select } from "../components/ui/Field";
import { Metric, MetricGrid } from "../components/ui/Metric";
import { EmptyState } from "../components/ui/State";
import { compact, money, pct, titleCase } from "../lib/format";
import { statusTone } from "../lib/status";
import { useAuditra, type ControlledEvaluationSettings } from "../hooks/useAuditra";
import type { AnomalyMode, FailureRecord, ReconciliationCase } from "../types/auditra";

const anomalyNames = [
  "AMOUNT_MISMATCH",
  "MISSING_SETTLEMENT",
  "DUPLICATE_PAYMENT",
  "FEE_MISMATCH",
  "REFUND_MISMATCH",
  "PARTIAL_SETTLEMENT",
  "TIMING_MISMATCH",
  "CONFLICTING_EVIDENCE",
  "CURRENCY_MISMATCH",
  "ENTITY_LINK_FAILURE",
];

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

export function EvaluationLabPage() {
  const { audit, comparison, runControlledEvaluation, breakController, runComparison, selectCase, isBusy } = useAuditra();
  const [settings, setSettings] = useState<ControlledEvaluationSettings>({
    recordCount: 500,
    seed: 91,
    anomalyMode: "STRESSED",
    anomalyRates: initialRates,
  });
  const comparisonRows = comparison?.comparison ?? audit?.comparison.comparison ?? [];
  const aiRow = comparisonRows.find((row) => row.mode === "ai_assisted");
  const baseRow = comparisonRows.find((row) => row.mode === "deterministic_only");

  function updateRate(name: string, value: string) {
    setSettings((current) => ({
      ...current,
      anomalyRates: {
        ...current.anomalyRates,
        [name]: value,
      },
    }));
  }

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader
          title="Evaluation Lab"
          kicker="Controlled worlds, controller breaks, failure replay and AI value measurement"
          action={<Button icon={<Scale className="h-4 w-4" />} disabled={!audit || isBusy} onClick={() => void runComparison()}>Run AI vs Baseline</Button>}
        />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <Field label="Records">
            <Input type="number" min={50} max={5000} value={settings.recordCount} onChange={(event) => setSettings({ ...settings, recordCount: Number(event.target.value) })} />
          </Field>
          <Field label="Seed">
            <Input type="number" value={settings.seed} onChange={(event) => setSettings({ ...settings, seed: Number(event.target.value) })} />
          </Field>
          <Field label="Anomaly Mode">
            <Select value={settings.anomalyMode} onChange={(event) => setSettings({ ...settings, anomalyMode: event.target.value as AnomalyMode })}>
              {["NORMAL", "STRESSED", "ADVERSARIAL", "CHAOS"].map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </Select>
          </Field>
          <div className="flex items-end">
            <Button className="w-full" variant="primary" icon={<FlaskConical className="h-4 w-4" />} disabled={isBusy} onClick={() => void runControlledEvaluation(settings)}>
              Run Controlled Evaluation
            </Button>
          </div>
          <div className="flex items-end">
            <Button className="w-full" variant="danger" disabled={isBusy} onClick={() => void breakController("CHAOS", settings.recordCount)}>
              Break Controller
            </Button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {anomalyNames.map((name) => (
            <Field key={name} label={name}>
              <Input value={settings.anomalyRates[name] ?? "0.0000"} onChange={(event) => updateRate(name, event.target.value)} />
            </Field>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(["STRESSED", "ADVERSARIAL", "CHAOS"] as AnomalyMode[]).map((mode) => (
            <Button key={mode} disabled={isBusy} onClick={() => void breakController(mode, settings.recordCount)}>
              {mode} Stress
            </Button>
          ))}
        </div>
      </Card>

      {audit ? (
        <>
          <MetricGrid>
            <Metric label="Evaluation Records" value={compact(audit.evaluation.metrics.confusion_matrix ? audit.controller_run.metrics.transactions_processed : 0)} />
            <Metric label="Accuracy" value={pct(audit.evaluation.metrics.accuracy)} tone="success" />
            <Metric label="F1" value={pct(audit.evaluation.metrics.f1)} />
            <Metric label="False Positive" value={pct(audit.evaluation.metrics.false_positive_rate)} tone={audit.evaluation.metrics.false_positive_rate ? "warning" : "success"} />
            <Metric label="False Negative" value={pct(audit.evaluation.metrics.false_negative_rate)} tone={audit.evaluation.metrics.false_negative_rate ? "warning" : "success"} />
            <Metric label="Error Impact" value={money(audit.evaluation.metrics.financial_impact_of_errors)} tone={Number(audit.evaluation.metrics.financial_impact_of_errors) ? "warning" : "success"} />
          </MetricGrid>

          <div className="grid gap-4 xl:grid-cols-2">
            <ComparisonChart rows={comparisonRows} />
            <FailureChart failures={audit.evaluation.metrics.failure_taxonomy} />
          </div>

          <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
            <AiValueSummary base={baseRow} ai={aiRow} />
            <ConfusionMatrix matrix={audit.evaluation.metrics.confusion_matrix} />
          </div>

          <Card>
            <SectionHeader title="Failure Replay" kicker={`${audit.evaluation.failures.length} evaluator failures`} />
            <DataTable rows={audit.evaluation.failures} columns={failureColumns(audit.controller_run.cases)} getRowId={(row) => row.case_id} onRowClick={(row) => selectCase(row.case_id)} emptyTitle="No failures recorded" />
          </Card>
        </>
      ) : (
        <EmptyState title="No evaluation results" detail="Run a controlled evaluation or a stress mode to populate charts and failure replay." />
      )}
    </div>
  );
}

function ComparisonChart({ rows }: { rows: Array<{ mode: string; metrics: { accuracy: number; precision: number; recall: number; f1: number; escalation_rate: number } }> }) {
  const data = rows.map((row) => ({
    mode: row.mode.replace("_", " "),
    accuracy: Number((row.metrics.accuracy * 100).toFixed(1)),
    precision: Number((row.metrics.precision * 100).toFixed(1)),
    recall: Number((row.metrics.recall * 100).toFixed(1)),
    f1: Number((row.metrics.f1 * 100).toFixed(1)),
    review: Number((row.metrics.escalation_rate * 100).toFixed(1)),
  }));
  if (!data.length) return <EmptyState title="No comparison rows" detail="Run AI vs baseline comparison for the active dataset." />;
  return (
    <Card>
      <SectionHeader title="AI vs Baseline Metrics" />
      <div className="h-80">
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="mode" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="accuracy" fill="#0f766e" />
            <Bar dataKey="precision" fill="#4338ca" />
            <Bar dataKey="recall" fill="#b45309" />
            <Bar dataKey="f1" fill="#be123c" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function FailureChart({ failures }: { failures: Record<string, number> }) {
  const data = Object.entries(failures).map(([name, count]) => ({ name: titleCase(name), count }));
  if (!data.length) return <EmptyState title="No failure taxonomy" detail="The current controller run produced no evaluator failures." />;
  return (
    <Card>
      <SectionHeader title="Failure Taxonomy" />
      <div className="h-80">
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#334155" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function AiValueSummary({
  base,
  ai,
}: {
  base?: { metrics: { accuracy: number; f1: number; financial_impact_of_errors: string; estimated_ai_cost_usd: string }; failures: number };
  ai?: { metrics: { accuracy: number; f1: number; financial_impact_of_errors: string; estimated_ai_cost_usd: string }; failures: number };
}) {
  if (!base || !ai) return <EmptyState title="No AI value comparison" detail="Run comparison after auditing a world." />;
  const accuracyDelta = ai.metrics.accuracy - base.metrics.accuracy;
  const f1Delta = ai.metrics.f1 - base.metrics.f1;
  const impactDelta = Number(base.metrics.financial_impact_of_errors) - Number(ai.metrics.financial_impact_of_errors);
  return (
    <Card>
      <SectionHeader title="Measured AI Value" kicker="Compared on the same dataset" />
      <div className="space-y-3">
        <ValueRow label="Accuracy Lift" value={pct(accuracyDelta, 2)} positive={accuracyDelta >= 0} />
        <ValueRow label="F1 Lift" value={pct(f1Delta, 2)} positive={f1Delta >= 0} />
        <ValueRow label="Failure Change" value={`${base.failures - ai.failures}`} positive={base.failures >= ai.failures} />
        <ValueRow label="Error Impact Avoided" value={money(impactDelta)} positive={impactDelta >= 0} />
        <ValueRow label="AI Cost" value={`USD ${ai.metrics.estimated_ai_cost_usd}`} positive />
      </div>
    </Card>
  );
}

function ValueRow({ label, value, positive }: { label: string; value: string; positive: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3">
      <span className="text-sm font-semibold text-muted">{label}</span>
      <Badge tone={positive ? "success" : "warning"}>{value}</Badge>
    </div>
  );
}

function ConfusionMatrix({ matrix }: { matrix: Record<string, Record<string, number>> }) {
  const labels = Object.keys(matrix).filter((label) => {
    const rowTotal = Object.values(matrix[label] ?? {}).reduce((sum, count) => sum + count, 0);
    const colTotal = Object.values(matrix).reduce((sum, row) => sum + (row[label] ?? 0), 0);
    return rowTotal + colTotal > 0;
  });
  if (!labels.length) return <EmptyState title="No confusion matrix" detail="Evaluation output did not include active labels." />;
  return (
    <Card>
      <SectionHeader title="Confusion Matrix" kicker="Expected by predicted status" />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="bg-slate-100 text-xs uppercase text-muted">
              <th className="border border-line px-2 py-2 text-left">Expected</th>
              {labels.map((label) => (
                <th key={label} className="border border-line px-2 py-2 text-right">{titleCase(label)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((expected) => (
              <tr key={expected}>
                <td className="border border-line px-2 py-2 font-bold text-ink">{titleCase(expected)}</td>
                {labels.map((predicted) => (
                  <td key={predicted} className="border border-line px-2 py-2 text-right font-mono">{matrix[expected]?.[predicted] ?? 0}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function failureColumns(cases: ReconciliationCase[]): Column<FailureRecord>[] {
  return [
    {
      key: "case",
      header: "Case",
      value: (row) => row.case_id,
      sortValue: (row) => row.case_id,
      className: "font-mono text-xs",
    },
    {
      key: "expected",
      header: "Expected",
      value: (row) => <Badge tone={statusTone(row.expected)}>{row.expected}</Badge>,
      sortValue: (row) => row.expected,
    },
    {
      key: "predicted",
      header: "Predicted",
      value: (row) => <Badge tone={statusTone(row.predicted)}>{row.predicted}</Badge>,
      sortValue: (row) => row.predicted,
    },
    {
      key: "category",
      header: "Category",
      value: (row) => titleCase(row.failure_category),
      sortValue: (row) => row.failure_category,
    },
    {
      key: "impact",
      header: "Impact",
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
