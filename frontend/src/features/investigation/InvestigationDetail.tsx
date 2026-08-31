import { executionLabel } from "../../lib/format";
import { ExternalLink, Send } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import { Metric, MetricGrid } from "../../components/ui/Metric";
import { EmptyState } from "../../components/ui/State";
import { money, pct, titleCase } from "../../lib/format";
import { riskTone, statusTone } from "../../lib/status";
import { CaseEvidenceFlow } from "../graph/RelationshipFlow";
import type { ReconciliationCase } from "../../types/auditra";
import { EvidencePanel } from "./EvidencePanel";
import { ToolTrace } from "./ToolTrace";
import { UnresolvedState } from "./UnresolvedState";
import { VerificationPanel } from "./VerificationPanel";

export function InvestigationDetail({
  item,
  onGraph,
  onRecords,
  onReview,
}: {
  item?: ReconciliationCase | null;
  onGraph: () => void;
  onRecords: () => void;
  onReview: () => void;
}) {
  if (!item) {
    return <EmptyState title="No investigation selected" detail="Open an exception or transaction to inspect the AI investigation, evidence and verification path." />;
  }

  const ai = item.ai_investigation;
  const selectedHypothesis = ai?.hypotheses.find((hypothesis) => hypothesis.hypothesis_id === ai.selected_hypothesis_id);

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs font-bold uppercase text-muted">Case ID</div>
            <h1 className="mt-1 break-all font-mono text-2xl font-black text-ink">{item.case_id}</h1>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone={statusTone(item.status)}>{item.status}</Badge>
              <Badge tone={riskTone(item.risk_score)}>Risk {item.risk_score.toFixed(1)}</Badge>
              {ai ? <Badge tone={ai.ai_unavailable ? "danger" : "review"}>{executionLabel(ai.mode)}</Badge> : <Badge tone="muted">AI not needed</Badge>}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button icon={<ExternalLink className="h-4 w-4" />} onClick={onGraph}>View Graph</Button>
            <Button onClick={onRecords}>View Records</Button>
            <Button variant="primary" icon={<Send className="h-4 w-4" />} onClick={onReview}>Send To Review</Button>
          </div>
        </div>
      </Card>

      <MetricGrid>
        <Metric label="Payment" value={item.payment_id} />
        <Metric label="Order" value={item.order_id ?? "-"} />
        <Metric label="Expected" value={money(item.decision.expected_settlement)} />
        <Metric label="Actual" value={money(item.decision.actual_settlement)} />
        <Metric label="Difference" value={item.decision.difference ?? "0.00"} tone={Number(item.decision.difference ?? 0) ? "warning" : "success"} />
        <Metric label="Impact" value={money(item.decision.financial_impact)} tone={Number(item.decision.financial_impact) ? "danger" : "success"} />
      </MetricGrid>

      <UnresolvedState item={item} onReview={onReview} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-4">
          <Card>
            <SectionHeader title="AI Investigation" kicker={ai?.objective || "Deterministic path did not request an AI investigation"} />
            {ai ? (
              <div className="space-y-3">
                <div className="rounded-lg border border-line bg-slate-50 p-3 text-sm leading-6 text-muted">{ai.rationale}</div>
                <div className="grid gap-3 md:grid-cols-3">
                  <Info label="Provider" value={`${ai.provider} / ${ai.model}`} />
                  <Info label="Tool Calls" value={String(ai.tool_call_count)} />
                  <Info label="Cost" value={`USD ${ai.estimated_cost_usd}`} />
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-line bg-slate-50 p-3 text-sm text-muted">The deterministic controller resolved this case without AI escalation.</div>
            )}
          </Card>

          <Card>
            <SectionHeader title="Hypotheses" kicker={selectedHypothesis ? `Selected: ${titleCase(selectedHypothesis.label)}` : "Evidence-first labels"} />
            <div className="grid gap-3 lg:grid-cols-2">
              {(ai?.hypotheses ?? []).map((hypothesis) => (
                <div key={hypothesis.hypothesis_id} className="rounded-lg border border-line bg-white p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-black uppercase text-ink">{titleCase(hypothesis.label)}</div>
                    <Badge tone={hypothesis.status === "SUPPORTED" ? "success" : hypothesis.status === "REJECTED" ? "danger" : "warning"}>
                      {hypothesis.status}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm text-muted">{pct(hypothesis.confidence)} confidence</div>
                  <div className="mt-2 text-sm leading-6 text-muted">{hypothesis.rationale}</div>
                  <div className="mt-3 grid gap-2 text-xs text-muted">
                    <div>Supporting: {hypothesis.supporting_evidence_ids.slice(0, 4).join(", ") || "-"}</div>
                    <div>Contradicting: {hypothesis.contradicting_evidence_ids.slice(0, 4).join(", ") || "-"}</div>
                  </div>
                </div>
              ))}
              {!ai?.hypotheses.length ? <div className="rounded-lg border border-line bg-slate-50 p-3 text-sm text-muted">No AI hypotheses attached.</div> : null}
            </div>
          </Card>
          <VerificationPanel verification={item.decision.verification} invariants={item.invariants} />
        </div>
        <div className="space-y-4">
          <Card>
            <SectionHeader title="Final Decision" />
            <div className="space-y-3">
              <Badge tone={statusTone(item.decision.status)}>{item.decision.status}</Badge>
              <div className="text-sm text-muted">Confidence {pct(item.decision.confidence_score)} / {item.decision.confidence_band}</div>
              <div className="text-sm text-muted">Reason codes: {item.decision.reason_codes.join(", ") || "-"}</div>
              <div className="grid gap-2">
                {Object.entries(item.decision.confidence_factors).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3 rounded-lg border border-line bg-slate-50 px-3 py-2 text-sm">
                    <span>{titleCase(key)}</span>
                    <span className="font-mono">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
          <Card>
            <SectionHeader title="Tool Activity" />
            <ToolTrace calls={item.tool_calls} />
          </Card>
        </div>
      </div>

      <EvidencePanel evidence={item.evidence} selectedIds={[...item.decision.supporting_evidence, ...item.decision.contradicting_evidence]} />
      <CaseEvidenceFlow graph={item.graph} />
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-white p-3">
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="mt-1 break-words text-sm font-bold text-ink">{value}</div>
    </div>
  );
}
