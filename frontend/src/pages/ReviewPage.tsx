import { ArrowRight, CheckCircle2, CircleAlert, GitBranch, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { InlineError, SectionTitle, SegmentedTabs, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { money, pct, titleCase } from "../lib/format";
import { caseEvidenceHighlights, caseShortExplanation, caseTitle, caseWhyItMatters, groupedReviewCases, reviewPriority } from "../lib/product";
import type { ReviewAction } from "../types/auditra";

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

  return <div className="space-y-7">
    <header className="animate-fade-up border-b border-white/10 pb-6"><StatusPill accent="amber" dot>Review</StatusPill><h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">Cases where Auditra needs you</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400 sm:text-base">Priority cases are sorted by impact, risk, and uncertainty. Technical traces stay behind details.</p></header>
    {lastReviewEvent ? <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm text-emerald-100">{lastReviewEvent}</div> : null}
    {error ? <InlineError error={error} /> : null}
    <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <WorkspacePanel>
        <SegmentedTabs tabs={[{ id: "high", label: "High", count: groups.high.length }, { id: "medium", label: "Medium", count: groups.medium.length }, { id: "resolved", label: "Resolved", count: groups.resolved.length }]} active={filter} onChange={setFilter} />
        <div className="mt-4 max-h-[660px] space-y-2 overflow-y-auto pr-1">{rows.length ? rows.map((item) => <button key={item.case_id} type="button" className={`w-full rounded-lg border p-4 text-left transition ${focus?.case_id === item.case_id ? "border-cyan-400/30 bg-cyan-400/10" : "border-white/10 bg-white/[0.035] hover:bg-white/[0.06]"}`} onClick={() => setSelectedCase(item)}><div className="flex items-start justify-between gap-3"><div><div className="text-sm font-semibold text-white">{caseTitle(item)}</div><div className="mt-1 text-xs text-slate-500">{reviewPriority(item)}</div></div><StatusPill accent={item.status === "MATCHED" ? "emerald" : "amber"}>{titleCase(item.status)}</StatusPill></div><p className="mt-3 line-clamp-2 text-xs leading-5 text-slate-500">{caseShortExplanation(item)}</p><div className="mt-3 text-sm font-semibold text-rose-200">{money(item.decision.financial_impact)}</div></button>) : <div className="rounded-lg border border-dashed border-white/10 p-8 text-center text-sm text-slate-500">No cases in this group.</div>}</div>
      </WorkspacePanel>
      {focus ? <div className="space-y-5">
        <WorkspacePanel className="border-amber-400/15"><SectionTitle icon={<ShieldAlert className="h-5 w-5" />} eyebrow={reviewPriority(focus)} title={caseTitle(focus)} detail={focus.payment_id} /><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Fact label="Decision" value={decisionLabel(focus.status)} /><Fact label="Confidence" value={pct(focus.decision.confidence_score)} /><Fact label="Exposure" value={money(focus.decision.financial_impact)} /><Fact label="Order" value={focus.order_id ?? "Unavailable"} /><Fact label="Payment" value={focus.payment_id} /><Fact label="Fee" value={money(focus.decision.expected_fee)} /><Fact label="GST" value={money(focus.decision.expected_gst)} /><Fact label="Refund" value={money(focus.decision.refund_total)} /><Fact label="Settlement expected" value={money(focus.decision.expected_settlement)} /><Fact label="Settlement actual" value={money(focus.decision.actual_settlement)} /><Fact label="Variance" value={money(focus.decision.difference ?? focus.decision.financial_impact)} /></div></WorkspacePanel>
        <div className="grid gap-5 lg:grid-cols-2"><TextPanel title="What happened?" text={caseShortExplanation(focus)} /><TextPanel title={focus.status === "HUMAN_REVIEW" || focus.status === "UNRESOLVED" ? "Why is it open?" : "Why?"} text={caseWhyItMatters(focus)} /></div>
        <WorkspacePanel><SectionTitle title="Evidence" detail="The key records Auditra used for this decision." /> <div className="mt-4 grid gap-3 md:grid-cols-3">{evidence.map((item) => <Fact key={item.evidence_id} label={titleCase(item.entity_type)} value={item.summary} />)}</div></WorkspacePanel><WorkspacePanel><SectionTitle icon={<GitBranch className="h-5 w-5" />} title="Evidence path" detail="Linked records from the live case graph." /><div className="mt-4 flex flex-wrap items-center gap-2">{focus.graph.nodes.filter((node) => ["Order", "Payment", "Refund", "FeeRule", "Settlement"].includes(node.type)).map((node, index, nodes) => <div key={node.id} className="flex items-center gap-2"><div className="rounded-md border border-[#c7ff54]/20 bg-[#c7ff54]/[0.06] px-3 py-2"><div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#77736e]">{node.type === "FeeRule" ? "Fee / GST" : node.type}</div><div className="mt-1 max-w-[170px] truncate text-xs font-semibold text-white">{node.label}</div></div>{index < nodes.length - 1 ? <ArrowRight className="h-4 w-4 text-[#f7c74d]" /> : null}</div>)}{!focus.graph.nodes.some((node) => node.type === "Settlement") ? <span className="rounded-md border border-[#ff6b4a]/25 bg-[#ff6b4a]/[0.08] px-3 py-2 text-xs font-semibold text-[#ffb08d]">Settlement evidence unavailable</span> : null}</div></WorkspacePanel>
        <WorkspacePanel><SectionTitle title="Verification" detail="Deterministic checks that support or challenge the result." /> <div className="mt-4 grid gap-2">{checks.slice(0, 5).map((check) => <div key={check.check} className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3">{check.passed ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-300" /> : <CircleAlert className="mt-0.5 h-4 w-4 text-rose-300" />}<div><div className="text-sm font-semibold text-white">{titleCase(check.check)}</div><div className="mt-1 text-xs leading-5 text-slate-500">{check.detail}</div></div></div>)}</div></WorkspacePanel>
        <WorkspacePanel><SectionTitle title="Decision" detail="Record the human decision for this controller run." /> <textarea className="mt-4 min-h-[100px] w-full rounded-lg border border-white/10 bg-black/25 p-3 text-sm text-white" value={note} onChange={(event) => setNote(event.target.value)} /><div className="mt-4 grid gap-3 sm:grid-cols-3"><Action label="Approve" disabled={isBusy} onClick={() => submit("APPROVE")} tone="emerald" /><Action label="Reject" disabled={isBusy} onClick={() => submit("REJECT")} tone="rose" /><Action label="Keep open" disabled={isBusy} onClick={() => submit("MARK_UNRESOLVED")} tone="amber" /></div></WorkspacePanel>
        <details className="rounded-lg border border-white/10 bg-slate-900/70 p-5"><summary className="cursor-pointer text-sm font-semibold text-white">View investigation details</summary><div className="mt-4 space-y-3 text-xs leading-5 text-slate-500"><div className="flex items-center gap-2 text-cyan-200"><GitBranch className="h-4 w-4" />{focus.graph.nodes.length} records / {focus.graph.edges.length} links</div><pre className="max-h-[360px] overflow-auto rounded-lg bg-black/30 p-4">{JSON.stringify({ ai: focus.ai_investigation, tools: focus.tool_calls, invariants: focus.invariants }, null, 2)}</pre></div></details>
      </div> : <Empty title="No case selected" detail="Choose a case from the queue." />}
    </div>
  </div>;
}

function decisionLabel(status: string) {
  if (["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED", "DUPLICATE"].includes(status)) return "AUTO_RESOLVE";
  if (status === "HUMAN_REVIEW") return "HUMAN_REVIEW";
  return "UNRESOLVED";
}

function Fact({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4"><div className="text-[11px] font-semibold text-slate-500">{label}</div><div className="mt-2 text-sm font-semibold text-white">{value}</div></div>; }
function TextPanel({ title, text }: { title: string; text: string }) { return <WorkspacePanel><div className="text-sm font-semibold text-white">{title}</div><p className="mt-3 text-sm leading-7 text-slate-400">{text}</p></WorkspacePanel>; }
function Action({ label, disabled, onClick, tone }: { label: string; disabled: boolean; onClick: () => void; tone: "emerald" | "rose" | "amber" }) { const cls = tone === "emerald" ? "bg-emerald-400 text-emerald-950" : tone === "rose" ? "bg-rose-500 text-white" : "bg-amber-300 text-amber-950"; return <button type="button" disabled={disabled} onClick={onClick} className={`min-h-11 rounded-md px-4 text-sm font-semibold transition hover:brightness-110 disabled:opacity-50 ${cls}`}>{label}</button>; }
function Empty({ title, detail, onClick }: { title: string; detail: string; onClick?: () => void }) { return <WorkspacePanel><div className="py-16 text-center"><h1 className="text-2xl font-semibold text-white">{title}</h1><p className="mt-2 text-sm text-slate-500">{detail}</p>{onClick ? <button type="button" className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-slate-950" onClick={onClick}>Open audits <ArrowRight className="h-4 w-4" /></button> : null}</div></WorkspacePanel>; }
