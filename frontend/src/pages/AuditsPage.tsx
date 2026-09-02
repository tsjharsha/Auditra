import {
  ArrowRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Crosshair,
  Database,
  Fingerprint,
  Gauge,
  GitCompare,
  LockKeyhole,
  Play,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { InlineError, MetricTile, ProgressBar, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { compact, money, pct, shortId, titleCase } from "../lib/format";
import { attentionCases, caseShortExplanation, caseTitle, potentialExposure } from "../lib/product";
import { cn } from "../lib/utils";
import type { AssuranceReport, FailureRecord, ReconciliationCase, RedTeamResult } from "../types/auditra";

const stages = ["Close", "Verify", "Inspect", "Challenge", "Assure"];

export function AuditsPage() {
  const {
    world,
    audit,
    assurance,
    redTeam,
    selectedCase,
    setSelectedCase,
    setActivePage,
    auditWorld,
    runRedTeam,
    isBusy,
    busyLabel,
    statusMessage,
    error,
  } = useAuditra();
  const [showAll, setShowAll] = useState(false);

  if (!world) {
    return <EmptyState title="No challenge batch is ready" detail="Choose a finance risk and generate an immutable batch first." action="Go to Build" onAction={() => setActivePage("home")} />;
  }

  if (!audit) {
    return <ControllerLaunch />;
  }

  const exceptions = attentionCases(audit);
  const failures = audit.evaluation.failures;
  const focus =
    (selectedCase && audit.controller_run.cases.find((item) => item.case_id === selectedCase.case_id)) ??
    audit.controller_run.cases.find((item) => failures.some((failure) => failure.case_id === item.case_id)) ??
    exceptions[0] ??
    audit.controller_run.cases[0];
  const focusFailure = failures.find((item) => item.case_id === focus?.case_id);
  const visibleCases = showAll ? exceptions : exceptions.slice(0, 8);

  return (
    <div className="space-y-7">
      <header className="rise-in border-b border-white/10 pb-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill accent={assurance ? recommendationAccent(assurance) : "cyan"} dot>
                {assurance ? titleCase(assurance.recommendation) : "Independent verification"}
              </StatusPill>
              <StatusPill accent="slate">{shortId(audit.controller_run.run_id, 20)}</StatusPill>
            </div>
            <h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">Controller audit</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[#aaa7a1] sm:text-base">
              The controller closed {compact(audit.controller_run.metrics.transactions_processed)} transactions. Auditra independently checked every decision against truth the controller never saw.
            </p>
          </div>
          <StoryRail active={redTeam ? 5 : assurance ? 4 : 2} />
        </div>
      </header>

      {isBusy ? (
        <div className="border-y border-[#c7ff54]/20 bg-[#c7ff54]/[0.06] px-5 py-4 text-sm text-[#d6ff82]">
          <span className="font-semibold">{busyLabel || "Working"}:</span> {statusMessage}
        </div>
      ) : null}
      {error ? <InlineError error={error} /> : null}

      <OutcomeSummary assurance={assurance} />

      <section>
        <SectionHeading
          icon={<ShieldAlert />}
          eyebrow="Exception ledger"
          title={exceptions.length ? compact(exceptions.length) + " decisions need attention" : "No unresolved exceptions"}
          detail="Every row is evidence-backed and traceable to the generated payment world."
        />
        <div className="mt-4 grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(460px,1.1fr)]">
          <WorkspacePanel className="p-0 sm:p-0">
            <div className="max-h-[620px] overflow-y-auto">
              {visibleCases.map((item) => (
                <LedgerRow
                  key={item.case_id}
                  item={item}
                  failure={failures.find((failure) => failure.case_id === item.case_id)}
                  active={focus?.case_id === item.case_id}
                  onClick={() => setSelectedCase(item)}
                />
              ))}
              {!visibleCases.length ? <div className="p-8 text-center text-sm text-emerald-200">Every decision was safely resolved.</div> : null}
            </div>
            {exceptions.length > 8 ? (
              <button type="button" className="w-full border-t border-white/10 px-4 py-3 text-sm font-semibold text-[#d6ff82] hover:bg-white/5" onClick={() => setShowAll((value) => !value)}>
                {showAll ? "Show priority exceptions" : `Show all ${exceptions.length} exceptions`}
              </button>
            ) : null}
          </WorkspacePanel>
          {focus ? <TruthDeepDive item={focus} failure={focusFailure} /> : null}
        </div>
      </section>

      {assurance ? <RedTeamStage report={assurance} result={redTeam} onRun={() => void runRedTeam(200)} disabled={isBusy} /> : null}
      {assurance ? <AssuranceStage report={redTeam?.assurance ?? assurance} retest={redTeam} /> : null}
    </div>
  );
}

function ControllerLaunch() {
  const { world, auditWorld, setActivePage, isBusy, busyLabel, statusMessage, error } = useAuditra();
  if (!world) return null;
  const pipeline = [
    ["Map relationships", "Orders, payments, refunds"],
    ["Reconcile settlements", "Amounts, timing, fees"],
    ["Investigate exceptions", "Bounded AI + tools"],
    ["Verify decisions", "Evidence and invariants"],
    ["Reveal ground truth", "Independent evaluation"],
  ];
  return (
    <div className="space-y-7">
      <header className="rise-in border-b border-white/10 pb-6">
        <StatusPill accent="emerald" dot>Batch validated / ground truth locked</StatusPill>
        <h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">Can the controller safely close this batch?</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[#aaa7a1] sm:text-base">
          It may auto-close safe transactions, explain known adjustments, or escalate uncertain decisions. It cannot access the hidden labels.
        </p>
      </header>
      <WorkspacePanel className="relative overflow-hidden">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_380px] xl:items-center">
          <div>
            <div className="flex items-center gap-3">
              <span className="grid h-12 w-12 place-items-center rounded-lg border border-[#f7c74d]/20 bg-[#f7c74d]/10 text-[#f7d778]"><BrainCircuit className="h-6 w-6" /></span>
              <div>
                <div className="text-xs font-semibold text-[#f7d778]">Finance controller</div>
                <h2 className="mt-1 text-xl font-semibold text-white">{world.challenge?.name ?? "Settlement reconciliation"}</h2>
              </div>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <LaunchMetric label="Transactions" value={compact(world.summary.payments)} />
              <LaunchMetric label="Payment volume" value={money(world.summary.payment_volume)} />
              <LaunchMetric label="Known anomalies" value={compact(world.summary.anomalies)} hidden />
            </div>
            <button
              type="button"
              className="button-primary mt-6"
              disabled={isBusy}
              onClick={() => void auditWorld()}
            >
              {isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
              {isBusy ? busyLabel || "Running controller" : "Run Finance controller"}
            </button>
            {isBusy ? <div className="mt-3 text-sm text-[#d6ff82]">{statusMessage}</div> : null}
          </div>
          <div className="space-y-2">
            {pipeline.map(([label, detail], index) => (
              <div key={label} className="flex items-center gap-3 rounded-lg border border-white/[0.07] bg-black/15 p-3">
                <span className={cn("grid h-7 w-7 shrink-0 place-items-center rounded-md text-xs font-bold", isBusy ? "animate-pulse bg-[#c7ff54]/15 text-[#d6ff82]" : "bg-white/5 text-[#77746e]")}>{index + 1}</span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-[#c7c4bf]">{label}</div>
                  <div className="mt-0.5 text-xs text-[#77746e]">{detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </WorkspacePanel>
      {error ? <InlineError error={error} /> : null}
      <button type="button" className="text-sm text-[#77746e] hover:text-white" onClick={() => setActivePage("home")}>Back to scenario</button>
    </div>
  );
}

function OutcomeSummary({ assurance }: { assurance: AssuranceReport | null }) {
  const { audit } = useAuditra();
  if (!audit) return null;
  const metrics = audit.controller_run.metrics;
  const exceptions = attentionCases(audit);
  const exposure = potentialExposure(exceptions);
  return (
    <section className="rise-in-delayed">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricTile label="Match rate" value={pct(metrics.match_rate, 1)} detail="Controller close rate" icon={<CheckCircle2 className="h-4 w-4" />} accent="emerald" />
        <MetricTile label="Auto-closed" value={compact(Math.round(metrics.automatic_resolution_rate * metrics.transactions_processed))} detail={pct(metrics.automatic_resolution_rate, 1) + " of batch"} icon={<Zap className="h-4 w-4" />} accent="cyan" />
        <MetricTile label="Escalated" value={compact(exceptions.length)} detail={pct(metrics.human_review_rate, 1) + " human review"} icon={<ShieldAlert className="h-4 w-4" />} accent={exceptions.length ? "amber" : "emerald"} />
        <MetricTile label="Potential exposure" value={money(exposure)} detail={money(audit.evaluation.metrics.financial_impact_of_errors) + " measured error"} icon={<Scale className="h-4 w-4" />} accent={exposure ? "rose" : "emerald"} />
        <MetricTile label="Assurance" value={assurance ? assurance.score.toFixed(1) : "..."} detail={assurance ? "Grade " + assurance.grade : "Verifying hidden truth"} icon={<Gauge className="h-4 w-4" />} accent={assurance ? recommendationAccent(assurance) : "indigo"} />
      </div>
    </section>
  );
}

function StoryRail({ active }: { active: number }) {
  return (
    <div className="flex min-w-[300px] items-center rounded-lg border border-white/10 bg-white/[0.035] p-2">
      {stages.map((stage, index) => (
        <div key={stage} className="flex flex-1 items-center">
          <div className="min-w-0 flex-1 text-center">
            <span className={cn("mx-auto grid h-7 w-7 place-items-center rounded-md text-xs font-bold", index < active ? "bg-emerald-300 text-emerald-950" : index === active ? "bg-[#c7ff54] text-[#1a2110]" : "bg-white/5 text-[#77746e]")}>
              {index < active ? <Check className="h-3.5 w-3.5" /> : index + 1}
            </span>
            <span className="mt-1 block truncate text-[10px] text-[#77746e]">{stage}</span>
          </div>
          {index < stages.length - 1 ? <ChevronRight className="h-3 w-3 shrink-0 text-[#77746e]" /> : null}
        </div>
      ))}
    </div>
  );
}

function LedgerRow({
  item,
  failure,
  active,
  onClick,
}: {
  item: ReconciliationCase;
  failure?: FailureRecord;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        "grid w-full grid-cols-[minmax(0,1fr)_auto] gap-3 border-b border-white/[0.07] p-4 text-left transition last:border-0",
        active ? "bg-[#c7ff54]/[0.06]" : "hover:bg-white/[0.035]",
      )}
      onClick={onClick}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-[#d6ff82]">{shortId(item.payment_id, 19)}</span>
          {failure ? <StatusPill accent="rose">Truth mismatch</StatusPill> : <StatusPill accent="amber">{titleCase(item.status)}</StatusPill>}
        </div>
        <div className="mt-2 text-sm font-semibold text-white">{caseTitle(item)}</div>
        <div className="mt-1 truncate text-xs text-[#77746e]">{caseShortExplanation(item)}</div>
      </div>
      <div className="text-right">
        <div className="text-sm font-semibold text-rose-200">{money(item.decision.financial_impact)}</div>
        <div className="mt-2 flex items-center justify-end gap-1 text-[11px] text-[#77746e]">Inspect <ChevronRight className="h-3 w-3" /></div>
      </div>
    </button>
  );
}

function TruthDeepDive({ item, failure }: { item: ReconciliationCase; failure?: FailureRecord }) {
  const expected = failure?.expected ?? item.status;
  const difference = item.decision.difference ?? item.decision.financial_impact;
  const failedChecks = item.decision.verification?.checks.filter((check) => !check.passed) ?? [];
  const graph = item.graph;
  return (
    <WorkspacePanel className="overflow-hidden border-[#c7ff54]/20">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-semibold text-[#d6ff82]">Ground truth verification</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{caseTitle(item)}</h3>
          <div className="mt-2 font-mono text-xs text-[#77746e]">{item.payment_id}</div>
        </div>
        <StatusPill accent={failure ? "rose" : "emerald"}>{failure ? "Decision challenged" : "Decision verified"}</StatusPill>
      </div>

      <div className="mt-5 grid gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10 sm:grid-cols-3">
        <TruthFact label="AI decision" value={titleCase(item.status)} tone={failure ? "amber" : "emerald"} />
        <TruthFact label="Hidden truth" value={titleCase(expected)} tone={failure ? "rose" : "emerald"} />
        <TruthFact label="Financial difference" value={money(difference)} tone={Number(difference) ? "rose" : "emerald"} />
      </div>

      <div className="mt-5 rounded-lg border border-white/10 bg-black/20 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white"><Fingerprint className="h-4 w-4 text-rose-300" /> Root cause</div>
        <p className="mt-2 text-sm leading-6 text-[#aaa7a1]">
          {failure?.root_cause ?? item.ai_investigation?.rationale ?? caseShortExplanation(item)}
        </p>
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs font-semibold text-[#aaa7a1]">Transaction evidence chain</div>
          <span className="text-[11px] text-[#77746e]">{graph.nodes.length} records / {graph.edges.length} links</span>
        </div>
        <div className="mt-3 flex max-w-full items-center gap-2 overflow-x-auto pb-2">
          {graph.nodes.slice(0, 6).map((node, index) => (
            <div key={node.id} className="flex shrink-0 items-center gap-2">
              <div className="min-w-[112px] rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="text-[10px] font-semibold uppercase text-[#d6ff82]">{node.type}</div>
                <div className="mt-1 max-w-[130px] truncate text-xs text-slate-300">{node.label}</div>
              </div>
              {index < Math.min(graph.nodes.length, 6) - 1 ? <ArrowRight className="h-3.5 w-3.5 text-[#77746e]" /> : null}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-2">
        {(failedChecks.length ? failedChecks : item.decision.verification?.checks.slice(0, 3) ?? []).map((check) => (
          <div key={check.check} className="flex gap-3 rounded-lg border border-white/[0.07] p-3">
            {check.passed ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> : <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />}
            <div>
              <div className="text-xs font-semibold text-slate-300">{titleCase(check.check)}</div>
              <div className="mt-1 text-xs leading-5 text-[#77746e]">{check.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </WorkspacePanel>
  );
}

function RedTeamStage({
  report,
  result,
  onRun,
  disabled,
}: {
  report: AssuranceReport;
  result: RedTeamResult | null;
  onRun: () => void;
  disabled: boolean;
}) {
  const fingerprint = report.failure_fingerprint;
  return (
    <section>
      <SectionHeading
        icon={<Crosshair />}
        eyebrow="Red team"
        title="Attack the controller where it is weakest"
        detail="Auditra turns the measured failure fingerprint into a new targeted, reproducible test batch."
      />
      <div className="mt-4 grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <WorkspacePanel className="border-rose-400/15">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <StatusPill accent={fingerprint.severity === "CRITICAL" ? "rose" : fingerprint.severity === "LOW" ? "emerald" : "amber"}>
                {fingerprint.severity} fingerprint
              </StatusPill>
              <h3 className="mt-4 text-2xl font-semibold text-white">{titleCase(fingerprint.pattern)}</h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[#aaa7a1]">{fingerprint.root_cause}</p>
            </div>
            <div className="grid min-w-[190px] grid-cols-2 gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10">
              <MiniFact label="Observed" value={compact(fingerprint.frequency)} />
              <MiniFact label="Exposure" value={money(fingerprint.exposure)} />
            </div>
          </div>
          <div className="mt-5">
            <div className="text-xs font-semibold text-[#77746e]">Targeted attack vectors</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {fingerprint.target_anomalies.map((anomaly) => <StatusPill key={anomaly} accent="rose">{titleCase(anomaly)}</StatusPill>)}
            </div>
          </div>
          {!result ? (
            <button
              type="button"
              className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-md border border-[#ff6b4a]/40 bg-[#ff6b4a]/10 px-5 text-sm font-semibold text-[#ffb08d] transition disabled:opacity-50"
              disabled={disabled}
              onClick={onRun}
            >
              {disabled ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4" />}
              Attack with 200 targeted cases
            </button>
          ) : (
            <div className="mt-6 rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
              Attack <span className="font-mono text-[#d6ff82]">{result.attack_id}</span> generated and independently scored.
            </div>
          )}
        </WorkspacePanel>
        {result ? <RetestComparison result={result} /> : <AttackPreview />}
      </div>
    </section>
  );
}

function RetestComparison({ result }: { result: RedTeamResult }) {
  const comparison = result.comparison;
  const survived = comparison.verdict === "SURVIVED";
  return (
    <WorkspacePanel className={survived ? "border-emerald-400/20" : "border-rose-400/20"}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold text-[#d6ff82]">Targeted retest</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{survived ? "Controller survived" : "Weakness confirmed"}</h3>
        </div>
        <StatusPill accent={survived ? "emerald" : "rose"}>{titleCase(comparison.verdict)}</StatusPill>
      </div>
      <div className="mt-6 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <ScoreBlock label="Original batch" score={comparison.baseline_score} failures={comparison.baseline_failures} />
        <ArrowRight className="h-5 w-5 text-[#77746e]" />
        <ScoreBlock label="Targeted attack" score={comparison.retest_score} failures={comparison.retest_failures} />
      </div>
      <div className="mt-5">
        <div className="flex justify-between text-xs text-[#77746e]"><span>Adversarial assurance</span><span>{comparison.retest_score.toFixed(1)} / 100</span></div>
        <div className="mt-2"><ProgressBar value={comparison.retest_score / 100} accent={survived ? "emerald" : "rose"} /></div>
      </div>
      <p className="mt-5 text-xs leading-5 text-[#77746e]">
        A lower targeted score is not hidden: it proves the evaluation found a real control boundary before production.
      </p>
    </WorkspacePanel>
  );
}

function AttackPreview() {
  return (
    <WorkspacePanel>
      <div className="grid h-full min-h-[280px] place-items-center text-center">
        <div>
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-lg border border-rose-400/20 bg-rose-400/10 text-rose-300"><Fingerprint className="h-7 w-7" /></span>
          <h3 className="mt-4 font-semibold text-white">Failure-directed generation</h3>
          <p className="mx-auto mt-2 max-w-xs text-sm leading-6 text-[#77746e]">New cases preserve hidden truth while increasing the exact anomaly mix linked to the observed weakness.</p>
        </div>
      </div>
    </WorkspacePanel>
  );
}

function AssuranceStage({ report, retest }: { report: AssuranceReport; retest: RedTeamResult | null }) {
  const tone = recommendationAccent(report);
  return (
    <section>
      <SectionHeading
        icon={<ShieldCheck />}
        eyebrow="Assurance report"
        title={retest ? "Final controller boundary" : "Initial deployment decision"}
        detail="A versioned score derived from accuracy, safe autonomy, escalation, anomaly recall, financial impact, and evidence coverage."
      />
      <div className="mt-4 overflow-hidden rounded-lg border border-white/10 bg-black/20">
        <div className="grid xl:grid-cols-[340px_minmax(0,1fr)]">
          <div className={cn("grid place-items-center border-b border-white/10 p-8 text-center xl:border-b-0 xl:border-r", tone === "emerald" ? "bg-emerald-400/[0.06]" : tone === "rose" ? "bg-rose-400/[0.06]" : "bg-amber-400/[0.06]")}>
            <div>
              <div className="text-xs font-semibold uppercase text-[#77746e]">Auditra assurance score</div>
              <div className="mt-4 text-7xl font-semibold text-white">{report.score.toFixed(1)}</div>
              <div className="mt-2 text-sm text-[#77746e]">Grade {report.grade} / 100</div>
              <StatusPill accent={tone} dot>{titleCase(report.recommendation)}</StatusPill>
              <p className="mx-auto mt-4 max-w-xs text-xs leading-5 text-[#77746e]">{report.recommendation_detail}</p>
            </div>
          </div>
          <div className="p-5 sm:p-7">
            <div className="grid gap-4 sm:grid-cols-2">
              {Object.entries(report.dimensions).map(([dimension, value]) => (
                <div key={dimension}>
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <span className="font-medium text-[#aaa7a1]">{titleCase(dimension)}</span>
                    <span className="font-semibold text-white">{pct(value, 1)}</span>
                  </div>
                  <div className="mt-2"><ProgressBar value={value} accent={value >= 0.9 ? "emerald" : value >= 0.75 ? "amber" : "rose"} /></div>
                </div>
              ))}
            </div>
            <div className="mt-7 grid gap-2 sm:grid-cols-2">
              {report.controls.map((control) => (
                <div key={control.control} className="flex gap-3 rounded-lg border border-white/[0.07] bg-black/15 p-3">
                  {control.status === "PASSED" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> : <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />}
                  <div>
                    <div className="text-xs font-semibold text-[#c7c4bf]">{control.control}</div>
                    <div className="mt-1 text-[11px] leading-5 text-[#77746e]">{control.detail}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/10 pt-4 text-[11px] text-[#77746e]">
              <span>Report {report.report_id}</span>
              <span>Model {report.model_version}</span>
              <span>{report.unsafe_auto_actions} unsafe auto-actions</span>
              <span>{money(report.unsafe_exposure)} unsafe exposure</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionHeading({ icon, eyebrow, title, detail }: { icon: ReactNode; eyebrow: string; title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[#c7ff54]/20 bg-[#c7ff54]/10 text-[#d6ff82] [&>svg]:h-5 [&>svg]:w-5">{icon}</span>
      <div>
        <div className="text-xs font-semibold text-[#d6ff82]">{eyebrow}</div>
        <h2 className="mt-1 text-xl font-semibold text-white">{title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-[#77746e]">{detail}</p>
      </div>
    </div>
  );
}

function EmptyState({ title, detail, action, onAction }: { title: string; detail: string; action: string; onAction: () => void }) {
  return (
    <WorkspacePanel>
      <div className="py-16 text-center">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-lg border border-[#f7c74d]/20 bg-[#f7c74d]/10 text-[#f7d778]"><Database className="h-7 w-7" /></span>
        <h1 className="mt-5 text-2xl font-semibold text-white">{title}</h1>
        <p className="mt-2 text-sm text-[#77746e]">{detail}</p>
        <button type="button" className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-slate-950" onClick={onAction}>{action}<ArrowRight className="h-4 w-4" /></button>
      </div>
    </WorkspacePanel>
  );
}

function LaunchMetric({ label, value, hidden = false }: { label: string; value: string; hidden?: boolean }) {
  return <div className="rounded-lg border border-white/10 bg-black/15 p-4"><div className="text-xs text-[#77746e]">{label}</div><div className={cn("mt-2 text-lg font-semibold", hidden ? "text-amber-200" : "text-white")}>{value}</div></div>;
}

function TruthFact({ label, value, tone }: { label: string; value: string; tone: "emerald" | "amber" | "rose" }) {
  const color = tone === "emerald" ? "text-emerald-200" : tone === "rose" ? "text-rose-200" : "text-amber-200";
  return <div className="bg-slate-950/80 p-4"><div className="text-xs text-[#77746e]">{label}</div><div className={cn("mt-2 text-sm font-semibold", color)}>{value}</div></div>;
}

function MiniFact({ label, value }: { label: string; value: string }) {
  return <div className="bg-slate-950/70 p-3 text-center"><div className="text-[10px] text-[#77746e]">{label}</div><div className="mt-1 text-sm font-semibold text-white">{value}</div></div>;
}

function ScoreBlock({ label, score, failures }: { label: string; score: number; failures: number }) {
  return <div className="rounded-lg border border-white/10 bg-black/15 p-4 text-center"><div className="text-[10px] text-[#77746e]">{label}</div><div className="mt-2 text-2xl font-semibold text-white">{score.toFixed(1)}</div><div className="mt-1 text-[11px] text-rose-300">{failures} failures</div></div>;
}

function recommendationAccent(report: AssuranceReport): "emerald" | "amber" | "rose" {
  if (report.recommendation === "CONTROLLED_DEPLOYMENT") return "emerald";
  if (report.recommendation === "HUMAN_SUPERVISED") return "amber";
  return "rose";
}
