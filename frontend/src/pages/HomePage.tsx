import {
  ArrowRight,
  Banknote,
  Bot,
  CheckCircle2,
  CircleAlert,
  Download,
  FileJson,
  Gauge,
  LockKeyhole,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { InlineError, MetricTile, ProgressBar, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { compact, executionLabel, money, pct, titleCase } from "../lib/format";
import { attentionCases, auditHealthLabel, auditHealthRatio, caseShortExplanation, caseTitle, potentialExposure } from "../lib/product";
import type { AuditWorldResult, ReconciliationCase } from "../types/auditra";

const closeLoop = ["Orders", "Payments", "Fees + GST", "Refunds", "Settlements", "Exceptions"];

export function HomePage() {
  const {
    world,
    audit,
    assurance,
    runtimeAI,
    buildChallenge,
    auditWorld,
    setActivePage,
    setSelectedCase,
    isBusy,
    busyLabel,
    statusMessage,
    error,
  } = useAuditra();
  const [recordCount, setRecordCount] = useState(500);
  const attention = attentionCases(audit);
  const exposure = potentialExposure(attention);
  const mode = runtimeAI?.investigation.execution_mode ?? "AI_UNAVAILABLE";
  const focus = attention[0] ?? audit?.controller_run.cases[0] ?? null;

  async function runClose() {
    const target = world ?? (await buildChallenge(recordCount));
    await auditWorld(target);
  }

  function openCase(item: ReconciliationCase | null) {
    if (item) setSelectedCase(item);
    setActivePage("review");
  }

  return (
    <div className="space-y-7">
      <section className="animate-fade-up overflow-hidden rounded-lg border border-white/10 bg-[radial-gradient(circle_at_18%_10%,rgba(34,211,238,0.24),transparent_34%),radial-gradient(circle_at_82%_18%,rgba(99,102,241,0.22),transparent_30%),linear-gradient(135deg,rgba(9,13,22,0.98),rgba(3,7,18,0.98))] p-5 shadow-[0_24px_80px_rgba(2,6,23,0.36)] sm:p-8 lg:p-10">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_430px] xl:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill accent="cyan" dot>Razorpay Payment Operations</StatusPill>
              <StatusPill accent={mode.startsWith("REAL_") ? "emerald" : mode === "AI_UNAVAILABLE" ? "rose" : "amber"}>{executionLabel(mode)}</StatusPill>
            </div>
            <h1 className="mt-5 max-w-4xl text-4xl font-semibold leading-tight text-white sm:text-6xl">
              AI Finance Controller for payment reconciliation.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300 sm:text-lg">
              Close a synthetic Razorpay-style batch across payments, refunds, fees, GST, and settlements. Auditra reports match rate, throughput, open exceptions, financial exposure, and the evidence behind every decision.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button
                type="button"
                className="inline-flex min-h-12 items-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-slate-950 shadow-[0_18px_44px_rgba(255,255,255,0.12)] transition hover:bg-cyan-50 disabled:opacity-50"
                disabled={isBusy}
                onClick={() => void buildChallenge(recordCount)}
              >
                {isBusy && busyLabel === "Building challenge" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Build batch
              </button>
              <button
                type="button"
                className="inline-flex min-h-12 items-center gap-2 rounded-md bg-gradient-to-r from-indigo-500 via-sky-500 to-cyan-400 px-6 text-sm font-semibold text-white shadow-[0_18px_44px_rgba(14,165,233,0.28)] transition hover:brightness-110 disabled:opacity-50"
                disabled={isBusy}
                onClick={() => void runClose()}
              >
                {isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
                Run controller
              </button>
              {audit ? (
                <button
                  type="button"
                  className="inline-flex min-h-12 items-center gap-2 rounded-md border border-white/10 bg-white/[0.06] px-5 text-sm font-semibold text-white transition hover:bg-white/[0.1]"
                  onClick={() => openCase(focus)}
                >
                  Inspect evidence <ArrowRight className="h-4 w-4" />
                </button>
              ) : null}
            </div>
            <div className="mt-4 text-sm text-cyan-100/80">{isBusy ? `${busyLabel}: ${statusMessage}` : statusMessage}</div>
          </div>

          <WorkspacePanel className="bg-black/25 p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold text-cyan-300">Submission batch</div>
                <div className="mt-1 text-lg font-semibold text-white">Synthetic finance close</div>
              </div>
              <LockKeyhole className="h-5 w-5 text-emerald-300" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {[100, 500, 1000].map((count) => (
                <button
                  key={count}
                  type="button"
                  className={`min-h-10 rounded-md border px-3 text-sm font-semibold transition ${recordCount === count ? "border-cyan-300 bg-cyan-300 text-slate-950" : "border-white/10 bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]"}`}
                  onClick={() => setRecordCount(count)}
                >
                  {compact(count)}
                </button>
              ))}
            </div>
            <div className="mt-5 grid gap-2">
              {closeLoop.map((item, index) => (
                <div key={item} className="flex items-center gap-3 rounded-md border border-white/[0.07] bg-white/[0.035] p-3">
                  <span className="grid h-7 w-7 place-items-center rounded-md bg-cyan-400/10 text-xs font-bold text-cyan-200">{index + 1}</span>
                  <span className="text-sm font-medium text-slate-200">{item}</span>
                </div>
              ))}
            </div>
          </WorkspacePanel>
        </div>
      </section>

      {error ? <InlineError error={error} /> : null}

      <section className="animate-fade-up-delayed grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Match rate" value={audit ? pct(audit.controller_run.metrics.match_rate, 1) : "Ready"} detail={audit ? "Closed and independently checked" : "Run the controller"} icon={<CheckCircle2 className="h-4 w-4" />} accent={audit ? "emerald" : "cyan"} />
        <MetricTile label="Open exceptions" value={audit ? compact(attention.length) : compact(world?.summary.anomalies)} detail={audit ? auditHealthLabel(audit) : "Hidden anomalies locked"} icon={<CircleAlert className="h-4 w-4" />} accent={attention.length ? "amber" : "emerald"} />
        <MetricTile label="Throughput" value={audit ? `${compact(audit.controller_run.metrics.throughput_records_per_sec)} / sec` : compact(world?.summary.payments)} detail={audit ? "Local controller speed" : "Payment records"} icon={<Timer className="h-4 w-4" />} accent="indigo" />
        <MetricTile label="Financial exposure" value={audit ? money(exposure) : money(world?.summary.payment_volume)} detail={audit ? `${money(audit.evaluation.metrics.financial_impact_of_errors)} measured error` : "Payment volume"} icon={<Banknote className="h-4 w-4" />} accent={exposure ? "rose" : "cyan"} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <WorkspacePanel className="animate-fade-up-delayed-2">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="text-xs font-semibold text-cyan-300">Controller evidence</div>
              <h2 className="mt-1 text-2xl font-semibold text-white">{audit ? "The close has been measured" : world ? "Batch ready for close" : "Build the payment batch first"}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                {audit
                  ? "The controller never saw hidden truth during reconciliation. Evaluation runs after the close and records what passed, what failed, and what needs human review."
                  : "Auditra generates a deterministic synthetic batch with hidden truth, then withholds that truth until independent evaluation."}
              </p>
            </div>
            {assurance ? <StatusPill accent={assurance.recommendation === "CONTROLLED_DEPLOYMENT" ? "emerald" : assurance.recommendation === "HUMAN_SUPERVISED" ? "amber" : "rose"}>Assurance {assurance.score.toFixed(1)}</StatusPill> : null}
          </div>

          {audit ? (
            <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="flex justify-between text-xs text-slate-500"><span>Hidden-truth accuracy</span><span>{pct(audit.evaluation.metrics.accuracy, 1)}</span></div>
                <div className="mt-2"><ProgressBar value={auditHealthRatio(audit)} accent="emerald" /></div>
                <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                  <Fact label="Auto-closed" value={pct(audit.controller_run.metrics.automatic_resolution_rate, 1)} />
                  <Fact label="Human review" value={pct(audit.controller_run.metrics.human_review_rate, 1)} />
                  <Fact label="LLM calls" value={compact(audit.controller_run.metrics.llm_calls)} />
                  <Fact label="Tool calls" value={compact(audit.controller_run.metrics.agent_tool_calls)} />
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-semibold text-amber-300">Priority exception</div>
                    <h3 className="mt-1 text-lg font-semibold text-white">{focus ? caseTitle(focus) : "No open exception"}</h3>
                  </div>
                  {focus ? <StatusPill accent="amber">{titleCase(focus.status)}</StatusPill> : <StatusPill accent="emerald">Verified</StatusPill>}
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-400">{focus ? caseShortExplanation(focus) : "Every transaction in this batch was safely resolved."}</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <button type="button" className="inline-flex min-h-10 items-center gap-2 rounded-md bg-white px-4 text-sm font-semibold text-slate-950" onClick={() => openCase(focus)}>Open evidence <ArrowRight className="h-4 w-4" /></button>
                  <button type="button" className="inline-flex min-h-10 items-center gap-2 rounded-md border border-white/10 px-4 text-sm font-semibold text-slate-300 hover:bg-white/[0.06]" onClick={() => downloadAuditJson(audit)}><FileJson className="h-4 w-4" />Audit JSON</button>
                  <button type="button" className="inline-flex min-h-10 items-center gap-2 rounded-md border border-white/10 px-4 text-sm font-semibold text-slate-300 hover:bg-white/[0.06]" onClick={() => downloadExceptionsCsv(audit)}><Download className="h-4 w-4" />Exceptions CSV</button>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <ProofPoint icon={<ShieldCheck />} label="Ground truth locked" detail="The controller cannot inspect answer labels." />
              <ProofPoint icon={<Bot />} label="Bounded AI" detail="AI investigates; deterministic controls verify." />
              <ProofPoint icon={<Gauge />} label="Measured result" detail="Accuracy, throughput, exceptions, and exposure." />
            </div>
          )}
        </WorkspacePanel>

        <WorkspacePanel className="animate-fade-up-delayed-2 border-cyan-400/15">
          <div className="text-xs font-semibold text-cyan-300">5-minute story</div>
          <h2 className="mt-1 text-xl font-semibold text-white">What Razorpay should remember</h2>
          <div className="mt-5 space-y-3">
            {[
              ["Close the books", "One payment batch, 50+ records minimum, full reconciliation loop."],
              ["Show the misses", "Honest exception list and financial impact, not a perfect-looking toy."],
              ["Prove trust", "Hidden-truth evaluation plus adversarial retest before deployment."],
            ].map(([label, detail], index) => (
              <div key={label} className="flex gap-3 rounded-md border border-white/[0.07] bg-white/[0.035] p-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-indigo-400/10 text-sm font-bold text-indigo-200">{index + 1}</span>
                <div>
                  <div className="text-sm font-semibold text-white">{label}</div>
                  <div className="mt-1 text-xs leading-5 text-slate-500">{detail}</div>
                </div>
              </div>
            ))}
          </div>
        </WorkspacePanel>
      </section>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-white/[0.07] bg-white/[0.035] p-3"><div className="text-[11px] text-slate-500">{label}</div><div className="mt-1 font-semibold text-white">{value}</div></div>;
}

function ProofPoint({ icon, label, detail }: { icon: ReactNode; label: string; detail: string }) {
  return <div className="rounded-lg border border-white/10 bg-black/20 p-4"><div className="text-cyan-300 [&>svg]:h-5 [&>svg]:w-5">{icon}</div><div className="mt-3 text-sm font-semibold text-white">{label}</div><div className="mt-1 text-xs leading-5 text-slate-500">{detail}</div></div>;
}

function downloadAuditJson(audit: AuditWorldResult) {
  const report = {
    product: "Auditra",
    positioning: "AI Finance Controller for Razorpay-style payment reconciliation",
    world: audit.world,
    controller_run: audit.controller_run,
    evaluation: audit.evaluation,
    comparison: audit.comparison,
    survival_status: audit.survival_status,
  };
  downloadText(`auditra-audit-${audit.evaluation.evaluation_run_id}.json`, JSON.stringify(report, null, 2), "application/json");
}

function downloadExceptionsCsv(audit: AuditWorldResult) {
  const failures = new Map(audit.evaluation.failures.map((failure) => [failure.case_id, failure]));
  const rows = attentionCases(audit).map((item) => {
    const failure = failures.get(item.case_id);
    return [
      item.case_id,
      item.payment_id,
      item.status,
      failure ? "MISMATCH" : "VERIFIED",
      item.decision.confidence_score,
      item.decision.financial_impact,
      item.risk_score,
      item.ai_investigation?.mode ?? "DETERMINISTIC",
      item.ai_investigation?.llm_calls ?? 0,
      item.tool_calls.length,
      failure?.root_cause ?? item.decision.reason_codes[0] ?? caseShortExplanation(item),
    ];
  });
  const header = ["case_id", "payment_id", "status", "hidden_truth_check", "confidence", "financial_impact", "risk_score", "ai_mode", "llm_calls", "tool_calls", "reason"];
  const csv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  downloadText(`auditra-exceptions-${audit.evaluation.evaluation_run_id}.csv`, csv, "text/csv");
}

function csvCell(value: unknown) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadText(filename: string, body: string, type: string) {
  const blob = new Blob([body], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
