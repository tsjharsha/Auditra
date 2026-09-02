import { ArrowRight, CheckCircle2, CircleAlert, Download, FileJson, LoaderCircle, Play, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { auditraApi } from "../api/client";
import { InlineError, StatusPill } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { compact, money, pct } from "../lib/format";
import { attentionCases, caseShortExplanation, caseTitle, potentialExposure } from "../lib/product";
import type { ControllerAlert, ReconciliationCase, SettlementBrief } from "../types/auditra";

export function HomePage() {
  const { world, audit, assurance, challenges, selectedChallengeId, setSelectedChallengeId, runtimeAI, buildChallenge, auditWorld, setActivePage, setSelectedCase, isBusy, busyLabel, statusMessage, error } = useAuditra();
  const [recordCount, setRecordCount] = useState(500);
  const [brief, setBrief] = useState<SettlementBrief | null>(null);
  const [briefError, setBriefError] = useState(false);
  const [exporting, setExporting] = useState<"report" | "exceptions" | null>(null);
  const activeChallenge = useMemo(() => challenges.find((item) => item.challenge_id === selectedChallengeId) ?? challenges[0], [challenges, selectedChallengeId]);
  const exceptions = attentionCases(audit);
  const focus = exceptions[0] ?? audit?.controller_run.cases[0] ?? null;
  const execution = audit?.controller_run.execution;
  const cashPosition = audit?.cash_position;
  const mode = runtimeAI?.investigation.execution_mode ?? "OFFLINE_AI";

  useEffect(() => {
    setBrief(null);
    setBriefError(false);
    if (!audit) return;
    void auditraApi.settlementBrief(audit.evaluation.evaluation_run_id).then(setBrief).catch(() => setBriefError(true));
  }, [audit?.evaluation.evaluation_run_id]);

  async function runController() {
    const target = world && world.challenge?.challenge_id === selectedChallengeId ? world : await buildChallenge(recordCount);
    await auditWorld(target);
  }

  function openCase(item: ReconciliationCase | null) {
    if (item) setSelectedCase(item);
    setActivePage("review");
  }

  async function exportReport() {
    if (!audit) return;
    setExporting("report");
    try { downloadText(`auditra-submission-${audit.evaluation.evaluation_run_id}.json`, JSON.stringify(await auditraApi.submissionReport(audit.evaluation.evaluation_run_id), null, 2), "application/json"); } finally { setExporting(null); }
  }

  async function exportExceptions() {
    if (!audit) return;
    setExporting("exceptions");
    try { downloadBlob(`auditra-exceptions-${audit.evaluation.evaluation_run_id}.csv`, await auditraApi.exceptionReportCsv(audit.evaluation.evaluation_run_id)); } finally { setExporting(null); }
  }

  return <div className="space-y-7 pb-8">
    <section className="control-header rise-in">
      <div className="control-header-grid">
        <div>
          <div className="product-name">AUDITRA</div>
          <h1 className="control-title">Finance control</h1>
          <p className="control-copy">Close a payment operations batch, surface the few exceptions that matter, and measure whether the controller earned trust.</p>
</div>
        <div className="control-config">
          <label className="control-label" htmlFor="operation">Operation</label>
          <select id="operation" className="control-select" value={selectedChallengeId} onChange={(event) => setSelectedChallengeId(event.target.value)}>
            {challenges.map((challenge) => <option key={challenge.challenge_id} value={challenge.challenge_id}>{challenge.operational_scenario ?? challenge.name}</option>)}
          </select>
          <div className="control-meta">{compact(recordCount)} records · Synthetic · Ground truth locked</div>
          <div className="mt-4 flex flex-wrap gap-2" aria-label="Record count">{[100, 500, 1000].map((count) => <button key={count} type="button" aria-pressed={recordCount === count} className={`record-option min-w-14 px-3 ${recordCount === count ? "record-option-active" : ""}`} onClick={() => setRecordCount(count)}>{compact(count)}</button>)}</div>
          <div className="mt-4 flex flex-wrap gap-2"><button type="button" className="button-primary" disabled={isBusy} onClick={() => void runController()}>{isBusy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}{isBusy ? busyLabel || "Running" : "Run Finance Close"}</button><button type="button" className="button-quiet" disabled={isBusy} onClick={() => void buildChallenge(recordCount)}><Sparkles className="h-4 w-4" />Build batch</button></div>
          <div className="control-status-row"><span className={`control-status ${mode.startsWith("REAL_") ? "" : "warning"}`}>AI investigation: {mode.startsWith("REAL_") ? "Live provider" : "Offline structured"}</span><span className="control-status">Money controls: deterministic</span></div>
        </div>
      </div>
      <div className="mt-4 min-h-5 text-sm text-[#9a9792]">{isBusy ? `${busyLabel}: ${statusMessage}` : statusMessage}</div>
    </section>

    {error ? <InlineError error={error} /> : null}

    {!audit ? <section className="border-b border-white/10 pb-5 text-sm text-[#9a9792]">{activeChallenge?.description ?? "Choose a controlled payment operation and run it against locked hidden truth."}</section> : <>
      <section className="cash-position rise-in-delayed">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="section-kicker">Cash position</div><h2 className="mt-1 text-2xl font-semibold text-white">What cash should this batch close with?</h2></div><StatusPill accent={cashPosition?.status === "WITHIN_TOLERANCE" ? "emerald" : cashPosition?.status === "PENDING_SETTLEMENT" ? "amber" : "rose"}>{cashPosition ? cashStatusLabel(cashPosition.status) : "Calculating"}</StatusPill></div>
        {cashPosition ? <div className="cash-grid mt-4"><CashValue label="Expected net settlement" value={money(cashPosition.expected_net_settlement)} detail={`${compact(cashPosition.expected_case_count)} payment expectations`} primary /><CashValue label="Recorded settlement" value={money(cashPosition.recorded_settlement)} detail="Recorded settlement evidence" /><CashValue label="Pending / unsettled" value={money(cashPosition.pending_unsettled)} detail={`${compact(cashPosition.unsettled_case_count)} settlement(s) not recorded`} tone={Number(cashPosition.pending_unsettled) ? "warning" : "positive"} /><CashValue label="Settlement variance" value={money(cashPosition.settlement_variance)} detail={`${compact(cashPosition.variance_case_count)} recorded variance case(s)`} tone={Number(cashPosition.settlement_variance) ? "danger" : "positive"} /></div> : null}
      </section>

      <section className="rise-in-delayed">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="section-kicker">Batch closed</div><h2 className="mt-1 text-2xl font-semibold text-white">Close result</h2></div><StatusPill accent={assurance ? assuranceAccent(assurance.recommendation) : "amber"}>{assurance ? assurance.recommendation.replace(/_/g, " ") : "Verifying"}</StatusPill></div>
        <div className="kpi-strip mt-4">
          <Kpi label="Match rate" value={pct(audit.controller_run.metrics.match_rate, 1)} detail="current batch" tone="positive" />
          <Kpi label="Throughput" value={`${compact(audit.controller_run.metrics.throughput_records_per_sec)}/s`} detail="records processed" />
          <Kpi label="Human review" value={compact(exceptions.length)} detail="needs attention" tone={exceptions.length ? "warning" : "positive"} />
          <Kpi label="Exposure" value={money(potentialExposure(exceptions))} detail="open financial impact" tone={exceptions.length ? "danger" : "positive"} />
          <Kpi label="Auto-resolution" value={pct(audit.controller_run.metrics.automatic_resolution_rate, 1)} detail="closed safely" tone="positive" />
          <Kpi label="Unresolved" value={pct(audit.controller_run.metrics.unresolved_rate, 1)} detail="no safe closure" tone={audit.controller_run.metrics.unresolved_rate ? "danger" : "positive"} />
        </div>
      </section>

      <section className="priority-case rise-in-delayed">
        <div className="priority-header"><div><div className="section-kicker text-[#f7d778]">Priority exception</div><h2 className="priority-title">{focus ? caseTitle(focus) : "No exception remains open"}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-[#aaa7a1]">{focus ? caseShortExplanation(focus) : "The controller closed every record safely."}</p></div><div><div className="section-kicker text-right">Financial exposure</div><div className="priority-exposure">{focus ? money(focus.decision.financial_impact) : money(0)}</div></div></div>
        {focus ? <><div className="evidence-state"><EvidenceState label="Payment" present={hasEvidence(focus, "Payment")} /><EvidenceState label="Refund" present={hasEvidence(focus, "Refund")} /><EvidenceState label="Fee / GST" present={hasEvidence(focus, "FeeRule")} /><EvidenceState label="Settlement" present={hasEvidence(focus, "Settlement")} /></div><div className="mt-4 flex flex-wrap gap-2"><button type="button" className="button-primary" onClick={() => openCase(focus)}><ShieldCheck className="h-4 w-4" />Investigate</button><button type="button" className="button-secondary" onClick={() => openCase(focus)}>Review case <ArrowRight className="h-4 w-4" /></button><button type="button" className="button-quiet" disabled={exporting !== null} onClick={() => void exportReport()}>{exporting === "report" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <FileJson className="h-4 w-4" />}Export audit</button><button type="button" className="button-quiet" disabled={exporting !== null} onClick={() => void exportExceptions()}>{exporting === "exceptions" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}Exceptions CSV</button></div></> : null}
      </section>

      <section className="controller-alerts">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="section-kicker">Controller alerts</div><h2 className="mt-1 text-xl font-semibold text-white">What needs attention now</h2></div><button type="button" className="button-quiet" onClick={() => setActivePage("review")}>Open review queue <ArrowRight className="h-4 w-4" /></button></div>
        <div className="mt-3 divide-y divide-white/[0.08] border-y border-white/10">{audit.controller_alerts.map((alert) => <AlertRow key={alert.alert_id} alert={alert} onOpen={() => openAlert(alert, audit.controller_run.cases, openCase)} />)}</div>
      </section>
      <section className="assurance-summary"><div><div className="section-kicker">Assurance</div><h2 className="mt-1 text-xl font-semibold text-white">Should this controller be trusted?</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-[#aaa7a1]">The controller sees evidence, not evaluator labels. Auditra verifies the close deterministically and reveals hidden truth only after the decision.</p><div className="assurance-flow mt-4"><span>Controller decision</span><span>Evidence</span><span>Deterministic verification</span><span>Hidden-truth evaluation</span></div></div><div className="lg:text-right"><div className="assurance-score">{assurance ? assurance.score.toFixed(1) : "…"}</div><div className="mt-1 text-sm text-[#aaa7a1]">Independent control score</div><div className="mt-2 text-xs text-[#77746e]">Measured financial error: {money(audit.evaluation.metrics.financial_impact_of_errors)}</div><button type="button" className="button-secondary mt-4" onClick={() => setActivePage("insights")}>View assurance <ArrowRight className="h-4 w-4" /></button></div></section>

      <details className="border-b border-white/10 pb-4"><summary className="cursor-pointer text-sm font-semibold text-[#c7c4bf]">Close brief and execution disclosure</summary><div className="mt-4 grid gap-6 lg:grid-cols-2"><div>{brief?.answers.slice(0, 3).map((answer) => <button key={answer.id} type="button" className="brief-answer" onClick={() => openCase(audit.controller_run.cases.find((item) => answer.supporting_case_ids.includes(item.case_id)) ?? focus)}><span className="text-sm font-semibold text-white">{answer.question}</span><span className="mt-1 block text-left text-sm leading-6 text-[#9a9792]">{answer.answer}</span></button>)}{!brief && !briefError ? <div className="text-sm text-[#9a9792]">Preparing close brief...</div> : null}{briefError ? <div className="text-sm text-[#ffb08d]">The close completed, but the optional brief could not load.</div> : null}</div><div className="space-y-3 text-sm"><Disclosure label="AI investigation" value={execution?.execution_mode.startsWith("REAL_") ? "Live provider" : "Offline structured"} /><Disclosure label="Provider calls" value={String(execution?.real_provider_calls ?? 0)} /><Disclosure label="Fallback" value={execution?.fallback_count ? "Rate-limited: offline fallback active" : "None"} /><Disclosure label="Financial controls" value="Deterministic" /></div></div></details>
    </>}
  </div>;
}

function CashValue({ label, value, detail, primary = false, tone }: { label: string; value: string; detail: string; primary?: boolean; tone?: "positive" | "warning" | "danger" }) { return <div className={`cash-value ${primary ? "cash-value-primary" : ""}`}><div className="kpi-label">{label}</div><div className={`cash-value-number ${tone ?? ""}`}>{value}</div><div className="kpi-detail">{detail}</div></div>; }
function AlertRow({ alert, onOpen }: { alert: ControllerAlert; onOpen: () => void }) { const interactive = Boolean(alert.case_id); return <button type="button" disabled={!interactive} className="alert-row" onClick={onOpen}><span className={`alert-severity alert-${alert.severity.toLowerCase()}`}>{alert.severity}</span><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-white">{alert.title}</span><span className="mt-1 block truncate text-xs text-[#9a9792]">{alert.payment_id ? `${alert.payment_id} · ` : ""}{alert.summary}</span></span><span className="text-right"><span className="block text-sm font-semibold text-[#ffb08d]">{money(alert.financial_exposure)}</span><span className="mt-1 block text-[11px] text-[#77746e]">Verification {alert.verification_state.toLowerCase()}</span></span></button>; }
function openAlert(alert: ControllerAlert, cases: ReconciliationCase[], openCase: (item: ReconciliationCase | null) => void) { openCase(alert.case_id ? cases.find((item) => item.case_id === alert.case_id) ?? null : null); }
function cashStatusLabel(status: string) { return status.replace(/_/g, " "); }
function Kpi({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: "positive" | "warning" | "danger" }) { return <div className="kpi-item"><div className="kpi-label">{label}</div><div className={`kpi-value ${tone ?? ""}`}>{value}</div><div className="kpi-detail">{detail}</div></div>; }
function EvidenceState({ label, present }: { label: string; present: boolean }) { return <div className="evidence-state-item">{present ? <CheckCircle2 className="h-4 w-4 text-[#70f0bf]" aria-hidden /> : <CircleAlert className="h-4 w-4 text-[#ffb08d]" aria-hidden />}<span>{label}</span></div>; }
function Disclosure({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-4 border-b border-white/[0.08] pb-3"><span className="text-[#9a9792]">{label}</span><span className="max-w-[65%] text-right font-semibold text-white">{value}</span></div>; }
function hasEvidence(item: ReconciliationCase, type: string) { return item.graph.nodes.some((node) => node.type === type); }
function assuranceAccent(recommendation: string) { if (recommendation === "CONTROLLED_DEPLOYMENT") return "emerald" as const; if (recommendation === "HUMAN_SUPERVISED") return "amber" as const; return "rose" as const; }
function downloadText(filename: string, body: string, type: string) { downloadBlob(filename, new Blob([body], { type })); }
function downloadBlob(filename: string, blob: Blob) { const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url); }