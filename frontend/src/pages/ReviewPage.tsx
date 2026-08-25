import { useMemo, useState } from "react";
import { CheckCircle2, GitBranch, ShieldAlert } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { Textarea } from "../components/ui/Field";
import { EmptyState, SuccessState } from "../components/ui/State";
import { EvidencePanel } from "../features/investigation/EvidencePanel";
import { ToolTrace } from "../features/investigation/ToolTrace";
import { VerificationPanel } from "../features/investigation/VerificationPanel";
import { CaseEvidenceFlow } from "../features/graph/RelationshipFlow";
import { money, pct, titleCase } from "../lib/format";
import { caseEvidenceHighlights, caseShortExplanation, caseTitle, caseWhyItMatters, groupedReviewCases, reviewPriority } from "../lib/product";
import { riskTone, statusTone } from "../lib/status";
import { useAuditra } from "../hooks/useAuditra";
import type { ReviewAction } from "../types/auditra";

type ReviewFilter = "high" | "medium" | "resolved";

export function ReviewPage() {
  const { audit, selectedCase, setSelectedCase, reviewCase, lastReviewEvent, isBusy } = useAuditra();
  const [filter, setFilter] = useState<ReviewFilter>("high");
  const [note, setNote] = useState("Reviewed in Auditra.");

  if (!audit) {
    return <EmptyState title="No cases to review" detail="Run an audit first so Auditra can surface the transactions that need your attention." />;
  }

  const groups = groupedReviewCases(audit);
  const currentRows = filter === "high" ? groups.high : filter === "medium" ? groups.medium : groups.resolved;
  const focusCase = selectedCase ?? groups.high[0] ?? groups.medium[0] ?? groups.resolved[0] ?? null;
  const evidence = focusCase ? caseEvidenceHighlights(focusCase) : [];

  const submit = (action: ReviewAction) => {
    if (focusCase) void reviewCase(focusCase.case_id, action, note);
  };

  return (
    <div className="space-y-6">
      {lastReviewEvent ? <SuccessState title={lastReviewEvent} detail="The decision was recorded for the active controller run." /> : null}

      <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Card className="rounded-[32px] border-white/70 bg-white/90 p-5">
          <SectionHeader title="Cases where Auditra needs you" kicker="Focus on priority first, then work through the rest." />
          <div className="grid gap-2">
            <FilterButton label="High priority" count={groups.high.length} active={filter === "high"} onClick={() => setFilter("high")} />
            <FilterButton label="Medium priority" count={groups.medium.length} active={filter === "medium"} onClick={() => setFilter("medium")} />
            <FilterButton label="Resolved" count={groups.resolved.length} active={filter === "resolved"} onClick={() => setFilter("resolved")} />
          </div>
          <div className="mt-4 space-y-3">
            {currentRows.length ? (
              currentRows.map((item) => (
                <button
                  key={item.case_id}
                  className={`w-full rounded-[24px] border p-4 text-left transition ${
                    focusCase?.case_id === item.case_id ? "border-indigo-200 bg-indigo-50/70" : "border-line bg-slate-50/80 hover:bg-white"
                  }`}
                  onClick={() => setSelectedCase(item)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-950">{caseTitle(item)}</div>
                      <div className="mt-1 text-sm text-muted">{money(item.decision.financial_impact)} exposure</div>
                    </div>
                    <Badge tone={riskTone(item.risk_score)}>Risk {item.risk_score.toFixed(1)}</Badge>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted">{caseShortExplanation(item)}</p>
                </button>
              ))
            ) : (
              <EmptyState title="No cases in this group" detail="Switch groups to review a different slice of the queue." />
            )}
          </div>
        </Card>

        {focusCase ? (
          <div className="space-y-4">
            <Card className="rounded-[32px] border-white/70 bg-[linear-gradient(135deg,rgba(255,251,235,0.92),rgba(255,255,255,0.96),rgba(224,231,255,0.80))] p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="grid h-11 w-11 place-items-center rounded-2xl bg-amber-50 text-amber-600">
                      <ShieldAlert className="h-5 w-5" />
                    </span>
                    <div>
                      <div className="text-sm font-medium text-slate-500">{reviewPriority(focusCase)}</div>
                      <h1 className="text-2xl font-semibold tracking-tight text-slate-950">{caseTitle(focusCase)}</h1>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge tone={statusTone(focusCase.status)}>{titleCase(focusCase.status)}</Badge>
                    <Badge tone={riskTone(focusCase.risk_score)}>Risk {focusCase.risk_score.toFixed(1)}</Badge>
                    <Badge tone={Number(focusCase.decision.financial_impact) > 0 ? "warning" : "muted"}>{money(focusCase.decision.financial_impact)} exposure</Badge>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/80 bg-white/90 px-4 py-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Result</div>
                  <div className="mt-2 text-lg font-semibold text-slate-950">{titleCase(focusCase.decision.status)}</div>
                  <div className="text-sm text-muted">{pct(focusCase.decision.confidence_score)} confidence</div>
                </div>
              </div>
            </Card>

            <div className="grid gap-4 xl:grid-cols-2">
              <InfoCard title="What Auditra found" content={caseShortExplanation(focusCase)} />
              <InfoCard title={focusCase.status === "HUMAN_REVIEW" || focusCase.status === "UNRESOLVED" ? "Why Auditra is uncertain" : "Why"} content={caseWhyItMatters(focusCase)} />
            </div>

            <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
              <SectionHeader title="Evidence" kicker="The key records behind this decision" />
              <div className="grid gap-3 md:grid-cols-3">
                {evidence.map((item) => (
                  <div key={item.evidence_id} className="rounded-2xl border border-line bg-slate-50/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{titleCase(item.entity_type)}</div>
                    <div className="mt-2 text-sm font-semibold text-slate-950">{item.summary}</div>
                  </div>
                ))}
                {!evidence.length ? <EmptyState title="No evidence highlighted" detail="Open advanced details to inspect the full evidence set." /> : null}
              </div>
            </Card>

            <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
              <SectionHeader title="Verification" kicker="The checks Auditra used to build confidence" />
              <div className="grid gap-3">
                {(focusCase.decision.verification?.checks ?? []).slice(0, 4).map((check) => (
                  <div key={check.check} className="flex items-start gap-3 rounded-2xl border border-line bg-slate-50/80 px-4 py-3">
                    <CheckCircle2 className={`mt-0.5 h-4 w-4 ${check.passed ? "text-emerald-600" : "text-amber-600"}`} />
                    <div>
                      <div className="text-sm font-semibold text-slate-950">{check.check}</div>
                      <div className="text-sm text-muted">{check.detail}</div>
                    </div>
                  </div>
                ))}
                {!focusCase.decision.verification?.checks.length ? <EmptyState title="No verification summary" detail="Auditra did not return a verification summary for this case." /> : null}
              </div>
            </Card>

            <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
              <SectionHeader title="What you can decide" kicker="Approve, reject, or keep the case open after reviewing the evidence." />
              <Textarea value={note} onChange={(event) => setNote(event.target.value)} className="min-h-[120px] rounded-[24px] border-line bg-slate-50/80" />
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <Button variant="success" disabled={isBusy} onClick={() => submit("APPROVE")}>Approve</Button>
                <Button variant="danger" disabled={isBusy} onClick={() => submit("REJECT")}>Reject</Button>
                <Button disabled={isBusy} onClick={() => submit("MARK_UNRESOLVED")}>Keep open</Button>
              </div>
            </Card>

            <details className="rounded-[32px] border border-white/70 bg-white/90 p-6 shadow-panel">
              <summary className="cursor-pointer text-sm font-semibold text-slate-950">View investigation details</summary>
              <div className="mt-5 space-y-5">
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
                  <Card className="rounded-[28px] bg-slate-50/70">
                    <SectionHeader title="Reasoning snapshot" kicker="Advanced context stays here by default." />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between rounded-2xl border border-line bg-white px-4 py-3">
                        <span className="text-sm font-medium text-slate-700">AI mode</span>
                        <Badge tone={focusCase.ai_investigation ? "review" : "muted"}>{focusCase.ai_investigation?.mode ?? "Not needed"}</Badge>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl border border-line bg-white px-4 py-3">
                        <span className="text-sm font-medium text-slate-700">Relationship graph</span>
                        <span className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700">
                          Explore
                          <GitBranch className="h-4 w-4" />
                        </span>
                      </div>
                      <div className="rounded-2xl border border-line bg-white p-4 text-sm leading-6 text-muted">
                        {focusCase.ai_investigation?.rationale ?? "This case was resolved without an AI investigation."}
                      </div>
                    </div>
                  </Card>
                  <VerificationPanel verification={focusCase.decision.verification} invariants={focusCase.invariants} />
                </div>

                <EvidencePanel
                  evidence={focusCase.evidence}
                  selectedIds={[...focusCase.decision.supporting_evidence, ...focusCase.decision.contradicting_evidence]}
                />
                <Card className="rounded-[28px] bg-white">
                  <SectionHeader title="Relationship graph" kicker="Supporting and contradicting evidence across the case" />
                  <CaseEvidenceFlow graph={focusCase.graph} />
                </Card>
                <Card className="rounded-[28px] bg-white">
                  <SectionHeader title="Tool activity" kicker="Technical execution details for this investigation" />
                  <ToolTrace calls={focusCase.tool_calls} />
                </Card>
              </div>
            </details>
          </div>
        ) : (
          <EmptyState title="No case selected" detail="Choose a case from the queue to open the review workspace." />
        )}
      </div>
    </div>
  );
}

function FilterButton({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-left transition ${active ? "border-indigo-200 bg-indigo-50/70" : "border-line bg-slate-50/80 hover:bg-white"}`} onClick={onClick}>
      <span className="text-sm font-medium text-slate-800">{label}</span>
      <Badge tone={active ? "review" : "muted"}>{count}</Badge>
    </button>
  );
}

function InfoCard({ title, content }: { title: string; content: string }) {
  return (
    <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
      <div className="text-sm font-semibold text-slate-950">{title}</div>
      <p className="mt-3 text-sm leading-7 text-muted">{content}</p>
    </Card>
  );
}
