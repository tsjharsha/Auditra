import { ArrowRight, CheckCircle2, CircleAlert, GitBranch, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { InlineError, SegmentedTabs, StatusPill } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { money, pct, titleCase } from "../lib/format";
import { caseEvidenceHighlights, caseShortExplanation, caseTitle, caseWhyItMatters, groupedReviewCases, reviewPriority } from "../lib/product";
import type { ReconciliationCase, ReviewAction } from "../types/auditra";

type Filter = "high" | "medium" | "resolved";

export function ReviewPage() {
  const { audit, selectedCase, setSelectedCase, reviewCase, lastReviewEvent, isBusy, error, setActivePage } = useAuditra();
  const [filter, setFilter] = useState<Filter>("high");
  const [note, setNote] = useState("Reviewed in Auditra.");
  if (!audit) return <Empty title="No cases to review" detail="Run an audit first so Auditra can surface the decisions that need attention." onClick={() => setActivePage("audits")} />;

  const groups = groupedReviewCases(audit);
  const rows = filter === "high" ? groups.high : filter === "medium" ? groups.medium : groups.resolved;
  const focus = selectedCase ?? groups.high[0] ?? groups.medium[0] ?? groups.resolved[0] ?? null;
  const evidence = focus ? caseEvidenceHighlights(focus) : [];
  const checks = focus?.decision.verification?.checks ?? [];
  const submit = (action: ReviewAction) => focus && void reviewCase(focus.case_id, action, note);

  return <div className="space-y-7 pb-8">
    <header className="border-b border-white/10 pb-5 rise-in"><div className="section-kicker">Review</div><h1 className="mt-1 text-2xl font-semibold text-white">Cases needing attention</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-[#aaa7a1]">Prioritized by financial impact, risk, and uncertainty. Investigation detail stays available without getting in the way of the decision.</p></header>
    {lastReviewEvent ? <div className="border-y border-[#70f0bf]/25 py-3 text-sm text-[#70f0bf]">{lastReviewEvent}</div> : null}
    {error ? <InlineError error={error} /> : null}
    <div className="grid gap-7 xl:grid-cols-[330px_minmax(0,1fr)]">
      <aside className="border-b border-white/10 pb-4 xl:border-b-0 xl:border-r xl:pr-5">
        <SegmentedTabs tabs={[{ id: "high", label: "High", count: groups.high.length }, { id: "medium", label: "Medium", count: groups.medium.length }, { id: "resolved", label: "Resolved", count: groups.resolved.length }]} active={filter} onChange={setFilter} />
        <div className="mt-3 max-h-[650px] overflow-y-auto">{rows.length ? rows.map((item) => <CaseRow key={item.case_id} item={item} active={focus?.case_id === item.case_id} onClick={() => setSelectedCase(item)} />) : <div className="py-8 text-center text-sm text-[#77746e]">No cases in this group.</div>}</div>
      </aside>
      {focus ? <CaseControl item={focus} evidence={evidence} checks={checks} note={note} setNote={setNote} submit={submit} disabled={isBusy} /> : <Empty title="No case selected" detail="Choose a case from the queue." />}
    </div>
  </div>;
}

function CaseRow({ item, active, onClick }: { item: ReconciliationCase; active: boolean; onClick: () => void }) {
  return <button type="button" className={`w-full border-b border-white/[0.08] px-1 py-4 text-left transition ${active ? "border-l-2 border-l-[#c7ff54] bg-white/[0.035] pl-3" : "hover:bg-white/[0.025]"}`} onClick={onClick}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="text-sm font-semibold text-white">{caseTitle(item)}</div><div className="mt-1 text-xs text-[#77746e]">{reviewPriority(item)}</div></div><div className="text-right text-sm font-semibold text-[#ffb08d]">{money(item.decision.financial_impact)}</div></div><p className="mt-2 line-clamp-2 text-xs leading-5 text-[#9a9792]">{caseShortExplanation(item)}</p></button>;
}

function CaseControl({ item, evidence, checks, note, setNote, submit, disabled }: { item: ReconciliationCase; evidence: ReturnType<typeof caseEvidenceHighlights>; checks: NonNullable<ReconciliationCase["decision"]["verification"]>["checks"]; note: string; setNote: (value: string) => void; submit: (action: ReviewAction) => void; disabled: boolean }) {
  const verificationFailed = checks.some((check) => !check.passed);
  return <section className="space-y-6">
    <div className="border-b border-[#f7c74d]/45 pb-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="section-kicker text-[#f7d778]">{reviewPriority(item)}</div><h2 className="mt-1 text-2xl font-semibold text-white">{caseTitle(item)}</h2><div className="mt-2 font-mono text-xs text-[#77746e]">{item.payment_id}</div></div><StatusPill accent={item.status === "HUMAN_REVIEW" || item.status === "UNRESOLVED" ? "amber" : "emerald"}>{decisionLabel(item.status)}</StatusPill></div><p className="mt-4 max-w-3xl text-sm leading-6 text-[#aaa7a1]">{caseShortExplanation(item)}</p></div>

    <div className="grid gap-px border-y border-white/10 bg-white/[0.07] sm:grid-cols-3"><CaseFact label="Exposure" value={money(item.decision.financial_impact)} tone="danger" /><CaseFact label="Confidence" value={pct(item.decision.confidence_score)} /><CaseFact label="Variance" value={money(item.decision.difference ?? item.decision.financial_impact)} tone={Number(item.decision.difference ?? item.decision.financial_impact) ? "danger" : "positive"} /></div>

    <section><div className="section-kicker">Evidence</div><div className="mt-3 grid gap-x-6 gap-y-0 border-y border-white/10 sm:grid-cols-2">{evidence.map((entry) => <div key={entry.evidence_id} className="border-b border-white/[0.08] py-3 last:border-b-0"><div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-[#77746e]">{titleCase(entry.entity_type)}</div><div className="mt-1 text-sm font-semibold text-white">{entry.summary}</div></div>)}</div></section>

    <section className="grid gap-6 lg:grid-cols-2"><div><div className="section-kicker">AI investigation</div><div className="mt-3 text-sm font-semibold text-white">{item.ai_investigation ? `${item.tool_calls.length} evidence checks completed` : "No AI investigation needed"}</div><p className="mt-2 text-sm leading-6 text-[#aaa7a1]">{caseWhyItMatters(item)}</p></div><div><div className="section-kicker">Deterministic verification</div><div className={`mt-3 text-sm font-semibold ${verificationFailed ? "text-[#ffb08d]" : "text-[#70f0bf]"}`}>{verificationFailed ? "FAILED" : "PASSED"}</div><p className="mt-2 text-sm leading-6 text-[#aaa7a1]">{verificationFailed ? "The controller cannot safely close this variance without human action." : "The deterministic controls support the controller decision."}</p></div></section>

    <section className="border-y border-white/10 py-5"><div className="section-kicker">Human decision</div><textarea aria-label="Review note" className="mt-3 min-h-[96px] w-full border border-white/10 bg-transparent p-3 text-sm text-white placeholder:text-[#77746e]" value={note} onChange={(event) => setNote(event.target.value)} /><div className="mt-3 flex flex-wrap gap-2"><Action label="Approve" disabled={disabled} onClick={() => submit("APPROVE")} tone="positive" /><Action label="Reject" disabled={disabled} onClick={() => submit("REJECT")} tone="danger" /><Action label="Keep open" disabled={disabled} onClick={() => submit("MARK_UNRESOLVED")} tone="warning" /></div></section>

    <details className="border-b border-white/10 pb-4"><summary className="cursor-pointer text-sm font-semibold text-[#c7c4bf]">Investigation trace and evidence graph</summary><div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[#9a9792]"><GitBranch className="h-4 w-4 text-[#c7ff54]" />{item.graph.nodes.length} records · {item.graph.edges.length} relationships</div><div className="mt-3 flex max-w-full gap-2 overflow-x-auto pb-2">{item.graph.nodes.slice(0, 6).map((node) => <div key={node.id} className="min-w-[120px] border-l border-[#c7ff54]/30 pl-3"><div className="text-[10px] font-semibold uppercase tracking-[0.07em] text-[#77746e]">{node.type === "FeeRule" ? "Fee / GST" : node.type}</div><div className="mt-1 truncate text-xs text-white">{node.label}</div></div>)}</div><pre className="mt-3 max-h-[300px] overflow-auto bg-black/20 p-3 text-xs leading-5 text-[#9a9792]">{JSON.stringify({ ai: item.ai_investigation, tools: item.tool_calls, invariants: item.invariants }, null, 2)}</pre></details>
  </section>;
}

function CaseFact({ label, value, tone }: { label: string; value: string; tone?: "positive" | "danger" }) { return <div className="bg-[#151515] px-4 py-3"><div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-[#77746e]">{label}</div><div className={`mt-1 text-lg font-semibold ${tone === "danger" ? "text-[#ffb08d]" : tone === "positive" ? "text-[#70f0bf]" : "text-white"}`}>{value}</div></div>; }
function Action({ label, disabled, onClick, tone }: { label: string; disabled: boolean; onClick: () => void; tone: "positive" | "danger" | "warning" }) { const cls = tone === "positive" ? "button-primary" : tone === "danger" ? "border border-[#ff6b4a]/40 bg-[#ff6b4a]/10 text-[#ffb08d]" : "border border-[#f7c74d]/40 bg-[#f7c74d]/10 text-[#f7d778]"; return <button type="button" disabled={disabled} onClick={onClick} className={`min-h-10 rounded-md px-4 text-sm font-semibold transition disabled:opacity-50 ${cls}`}>{label}</button>; }
function decisionLabel(status: string) { if (["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED", "DUPLICATE"].includes(status)) return "AUTO RESOLVED"; if (status === "HUMAN_REVIEW") return "HUMAN REVIEW"; return "UNRESOLVED"; }
function Empty({ title, detail, onClick }: { title: string; detail: string; onClick?: () => void }) { return <section className="border-y border-white/10 py-12 text-center"><h1 className="text-2xl font-semibold text-white">{title}</h1><p className="mt-2 text-sm text-[#9a9792]">{detail}</p>{onClick ? <button type="button" className="button-secondary mt-5" onClick={onClick}>Open audit <ArrowRight className="h-4 w-4" /></button> : null}</section>; }