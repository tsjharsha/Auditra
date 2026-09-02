import {
  ArrowRight, Check, ChevronRight, CircleAlert, Download, FileJson, Gauge,
  Layers3, LoaderCircle, LockKeyhole, Play, Sparkles, Timer, WalletCards,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { auditraApi } from "../api/client";
import { InlineError, MetricTile, ProgressBar, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { compact, money, pct, titleCase } from "../lib/format";
import { attentionCases, caseShortExplanation, caseTitle, potentialExposure } from "../lib/product";
import type { ReconciliationCase, SettlementBrief } from "../types/auditra";

const flow = ["Capture", "Reconcile", "Review", "Close"];

export function HomePage() {
  const {
    world, audit, assurance, challenges, selectedChallengeId, setSelectedChallengeId, runtimeAI,
    buildChallenge, auditWorld, setActivePage, setSelectedCase, isBusy, busyLabel, statusMessage, error,
  } = useAuditra();
  const [recordCount, setRecordCount] = useState(500);
  const [brief, setBrief] = useState<SettlementBrief | null>(null);
  const [briefError, setBriefError] = useState(false);
  const [exporting, setExporting] = useState<"report" | "exceptions" | null>(null);
  const activeChallenge = useMemo(
    () => challenges.find((item) => item.challenge_id === selectedChallengeId) ?? challenges[0],
    [challenges, selectedChallengeId],
  );
  const exceptions = attentionCases(audit);
  const focus = exceptions[0] ?? audit?.controller_run.cases[0] ?? null;
  const exposure = potentialExposure(exceptions);
  const execution = audit?.controller_run.execution;
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
    try {
      const report = await auditraApi.submissionReport(audit.evaluation.evaluation_run_id);
      downloadText("auditra-submission-" + audit.evaluation.evaluation_run_id + ".json", JSON.stringify(report, null, 2), "application/json");
    } finally {
      setExporting(null);
    }
  }

  async function exportExceptions() {
    if (!audit) return;
    setExporting("exceptions");
    try {
      downloadBlob("auditra-exceptions-" + audit.evaluation.evaluation_run_id + ".csv", await auditraApi.exceptionReportCsv(audit.evaluation.evaluation_run_id));
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="space-y-6 pb-8">
      <section className="hero-surface rise-in">
        <div className="hero-grid">
          <div className="max-w-3xl">
            <div className="eyebrow-row"><span className="signal-dot" />Payment operations<span className="eyebrow-divider" />Reconciliation workspace</div>
            <h1 className="hero-title">Close the settlement batch with confidence.</h1>
            <p className="hero-copy">Auditra reconciles payments, fees, refunds, and settlements, then brings the few decisions that need a human to the surface.</p>
            <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-[#c7ff54]">Do not trust the AI. Measure whether you should.</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button type="button" className="button-secondary" disabled={isBusy} onClick={() => void buildChallenge(recordCount)}>
                {isBusy && busyLabel === "Building challenge" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Build batch
              </button>
              <button type="button" className="button-primary" disabled={isBusy} onClick={() => void runController()}>
                {isBusy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />} Run audit
              </button>
              {audit ? <button type="button" className="button-quiet" onClick={() => openCase(focus)}>Review priority case <ArrowRight className="h-4 w-4" /></button> : null}
            </div>
            <div className="mt-4 flex min-h-5 items-center gap-2 text-sm text-[#9a9792]">
              {isBusy ? <span className="inline-flex h-4 w-4 rounded-full border-2 border-[#c7ff54]/30 border-t-[#c7ff54] animate-spin" /> : null}
              {isBusy ? busyLabel + ": " + statusMessage : statusMessage}
            </div>
          </div>

          <aside className="batch-card">
            <div className="flex items-center justify-between">
              <div><div className="section-kicker">Batch configuration</div><div className="mt-1 text-lg font-semibold text-white">{activeChallenge?.operational_scenario ?? "Settlement close"}</div></div>
              <LockKeyhole className="h-5 w-5 text-[#c7ff54]" />
            </div>
            <div className="mt-5 grid grid-cols-3 gap-2">
              {[100, 500, 1000].map((count) => <button key={count} type="button" className={"record-option " + (recordCount === count ? "record-option-active" : "")} onClick={() => setRecordCount(count)}>{compact(count)}</button>)}
            </div>
            <div className="mt-5 border-t border-white/10 pt-4">
              <div className="flex items-center justify-between text-xs text-[#9a9792]"><span>AI execution</span><span className={mode.startsWith("REAL_") ? "text-[#70f0bf]" : "text-[#f7c74d]"}>{mode.startsWith("REAL_") ? "Live provider" : "Offline structured"}</span></div>
              <p className="mt-2 text-sm leading-6 text-[#c7c4bf]">Financial controls remain deterministic in every execution mode.</p>
            </div>
          </aside>
        </div>
      </section>

      <section className="rise-in-delayed">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><div className="section-kicker">Choose the operation</div><h2 className="mt-1 text-xl font-semibold text-white">What should this batch prove?</h2></div><span className="text-sm text-[#9a9792]">Synthetic records, locked truth, repeatable seed.</span></div>
        <div className="scenario-grid mt-4">
          {challenges.slice(0, 4).map((challenge, index) => {
            const selected = challenge.challenge_id === selectedChallengeId;
            return <button key={challenge.challenge_id} type="button" className={"scenario-option " + (selected ? "scenario-option-active" : "")} onClick={() => setSelectedChallengeId(challenge.challenge_id)}>
              <span className="scenario-index">0{index + 1}</span>
              <span className="mt-4 block text-left text-base font-semibold text-white">{challenge.operational_scenario ?? challenge.name}</span>
              <span className="mt-2 block text-left text-sm leading-5 text-[#9a9792]">{challenge.description}</span>
              {selected ? <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[#c7ff54]">Selected <Check className="h-3.5 w-3.5" /></span> : null}
            </button>;
          })}
          {!challenges.length ? <div className="scenario-option animate-pulse text-sm text-[#9a9792]">Loading operations...</div> : null}
        </div>
      </section>

      {error ? <InlineError error={error} /> : null}

      {!audit ? <section className="process-strip rise-in-delayed-2">
        {flow.map((item, index) => <div key={item} className="process-step"><span className="process-number">{index + 1}</span><span className="text-sm font-semibold text-white">{item}</span>{index < flow.length - 1 ? <ChevronRight className="process-arrow" /> : null}</div>)}
        <p className="col-span-full mt-1 max-w-2xl text-sm leading-6 text-[#9a9792]">The controller does not see the answer labels. It reconciles the batch first; hidden-truth evaluation happens only after the run.</p>
      </section> : <>
        <section className="rise-in-delayed">
          <div className="result-header"><div><div className="section-kicker">Batch close result</div><h2 className="mt-1 text-2xl font-semibold text-white">Here is what needs attention.</h2></div><StatusPill accent={assurance ? assuranceAccent(assurance.recommendation) : "amber"}>{assurance ? assurance.recommendation.replace(/_/g, " ") : "Verifying close"}</StatusPill></div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <MetricTile label="Match rate" value={pct(audit.controller_run.metrics.match_rate, 1)} detail="All records reconciled" icon={<Check className="h-4 w-4" />} accent="emerald" />
            <MetricTile label="Auto-resolution" value={pct(audit.controller_run.metrics.automatic_resolution_rate, 1)} detail="Closed without a human" icon={<Gauge className="h-4 w-4" />} accent="cyan" />
            <MetricTile label="Human review" value={pct(audit.controller_run.metrics.human_review_rate, 1)} detail={compact(exceptions.length) + " priority cases"} icon={<CircleAlert className="h-4 w-4" />} accent={exceptions.length ? "amber" : "emerald"} />
            <MetricTile label="Unresolved" value={pct(audit.controller_run.metrics.unresolved_rate, 1)} detail="No safe closure" icon={<WalletCards className="h-4 w-4" />} accent={audit.controller_run.metrics.unresolved_rate ? "rose" : "emerald"} />
            <MetricTile label="Throughput" value={compact(audit.controller_run.metrics.throughput_records_per_sec) + "/s"} detail={compact(audit.controller_run.metrics.transactions_processed) + " transactions processed"} icon={<Timer className="h-4 w-4" />} accent="cyan" />
            <MetricTile label="Financial error" value={money(audit.evaluation.metrics.financial_impact_of_errors)} detail="Measured after truth reveal" icon={<WalletCards className="h-4 w-4" />} accent={Number(audit.evaluation.metrics.financial_impact_of_errors) ? "rose" : "emerald"} />
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
          <WorkspacePanel className="case-spotlight">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="section-kicker text-[#ffb08d]">Priority decision</div><h2 className="mt-1 text-xl font-semibold text-white">{focus ? caseTitle(focus) : "Everything tied out"}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-[#c7c4bf]">{focus ? caseShortExplanation(focus) : "No financial decision remains open in this batch."}</p></div><StatusPill accent={focus ? "amber" : "emerald"}>{focus ? decisionLabel(focus.status) : "AUTO_RESOLVE"}</StatusPill></div>
            {focus ? <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Fact label="Order" value={focus.order_id ?? "Unavailable"} /><Fact label="Payment" value={focus.payment_id} /><Fact label="Fee" value={money(focus.decision.expected_fee)} /><Fact label="GST" value={money(focus.decision.expected_gst)} /><Fact label="Refund" value={money(focus.decision.refund_total)} /><Fact label="Expected settlement" value={money(focus.decision.expected_settlement)} /><Fact label="Actual settlement" value={money(focus.decision.actual_settlement)} /><Fact label="Variance" value={money(focus.decision.difference ?? focus.decision.financial_impact)} emphasis /></div> : null}
            <div className="mt-6 flex flex-wrap gap-3">
              <button type="button" className="button-primary" onClick={() => openCase(focus)}>Inspect evidence <ArrowRight className="h-4 w-4" /></button>
              <button type="button" className="button-secondary" disabled={exporting !== null} onClick={() => void exportReport()}>{exporting === "report" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <FileJson className="h-4 w-4" />} Audit report</button>
              <button type="button" className="button-quiet" disabled={exporting !== null} onClick={() => void exportExceptions()}>{exporting === "exceptions" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Exception CSV</button>
            </div>
          </WorkspacePanel>
          <WorkspacePanel className="assurance-panel">
            <div className="section-kicker">Close assurance</div>
            <div className="mt-3 flex items-end justify-between gap-3"><div><div className="text-4xl font-semibold text-white">{assurance ? assurance.score.toFixed(1) : "..."}</div><div className="mt-1 text-sm text-[#9a9792]">Independent control score</div></div><Gauge className="h-9 w-9 text-[#c7ff54]" /></div>
            <div className="mt-5"><ProgressBar value={(assurance?.score ?? 0) / 100} accent={assurance ? assuranceAccent(assurance.recommendation) : "amber"} /></div>
            <p className="mt-5 text-sm leading-6 text-[#c7c4bf]">{assurance?.recommendation_detail ?? "Hidden-truth evaluation is checking how safely this controller closed the batch."}</p>
            <button type="button" className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#c7ff54]" onClick={() => setActivePage("audits")}>See controls and retest <ArrowRight className="h-4 w-4" /></button>
          </WorkspacePanel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]">
          <WorkspacePanel>
            <div className="flex items-center justify-between gap-4"><div><div className="section-kicker">Operational brief</div><h2 className="mt-1 text-xl font-semibold text-white">Answers from this close</h2></div><Layers3 className="h-5 w-5 text-[#f7c74d]" /></div>
            <div className="mt-5 grid gap-3">{brief?.answers.map((answer) => <button key={answer.id} type="button" className="brief-answer" onClick={() => openCase(audit.controller_run.cases.find((item) => answer.supporting_case_ids.includes(item.case_id)) ?? focus)}><span className="text-sm font-semibold text-white">{answer.question}</span><span className="mt-1 block text-left text-sm leading-6 text-[#9a9792]">{answer.answer}</span></button>)}
              {!brief && !briefError ? <div className="py-6 text-sm text-[#9a9792]">Preparing the close brief...</div> : null}
              {briefError ? <div className="py-3 text-sm text-[#ffb08d]">The close completed, but the optional operational brief could not load.</div> : null}
            </div>
            {brief ? <p className="mt-4 text-xs leading-5 text-[#77736e]">{brief.disclosure}</p> : null}
          </WorkspacePanel>
          <WorkspacePanel>
            <div className="section-kicker">Execution disclosure</div><h2 className="mt-1 text-xl font-semibold text-white">What powered this run?</h2>
            <div className="mt-5 space-y-3"><ExecutionRow label="Investigation mode" value={execution?.execution_mode.startsWith("REAL_") ? "Live provider" : "Offline structured controller"} tone={execution?.execution_mode.startsWith("REAL_") ? "mint" : "yellow"} /><ExecutionRow label="Provider calls" value={String(execution?.real_provider_calls ?? 0)} /><ExecutionRow label="Fallbacks" value={execution?.fallback_count ? "Provider rate-limited / offline fallback active" : "0"} tone={execution?.fallback_count ? "yellow" : "mint"} /><ExecutionRow label="AI role" value="Investigate only; controls decide" /></div>
            <p className="mt-5 text-xs leading-5 text-[#77736e]">Money math, invariants, and final verification are deterministic in every run.</p>
          </WorkspacePanel>
        </section>
      </>}
    </div>
  );
}

function decisionLabel(status: string) {
  if (["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED", "DUPLICATE"].includes(status)) return "AUTO_RESOLVE";
  if (status === "HUMAN_REVIEW") return "HUMAN_REVIEW";
  return "UNRESOLVED";
}

function Fact({ label, value, emphasis = false }: { label: string; value: string; emphasis?: boolean }) {
  return <div className={"fact-box " + (emphasis ? "fact-box-emphasis" : "")}><div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#77736e]">{label}</div><div className="mt-2 text-lg font-semibold text-white">{value}</div></div>;
}

function ExecutionRow({ label, value, tone }: { label: string; value: string; tone?: "mint" | "yellow" }) {
  const color = tone === "mint" ? "text-[#70f0bf]" : tone === "yellow" ? "text-[#f7c74d]" : "text-white";
  return <div className="flex items-center justify-between gap-4 border-b border-white/[0.07] pb-3 text-sm last:border-0 last:pb-0"><span className="text-[#9a9792]">{label}</span><span className={"max-w-[65%] text-right font-semibold " + color}>{value}</span></div>;
}

function assuranceAccent(recommendation: string) {
  if (recommendation === "CONTROLLED_DEPLOYMENT") return "emerald" as const;
  if (recommendation === "HUMAN_SUPERVISED") return "amber" as const;
  return "rose" as const;
}

function downloadText(filename: string, body: string, type: string) { downloadBlob(filename, new Blob([body], { type })); }
function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
