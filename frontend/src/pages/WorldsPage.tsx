import { ArrowRight, Eye, FileText, PlayCircle, RefreshCw, ShieldCheck, WandSparkles } from "lucide-react";
import { InlineError, MetricTile, SectionTitle, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { PROMPT_SUGGESTIONS, useAuditra } from "../hooks/useAuditra";
import { compact, money, titleCase } from "../lib/format";

export function WorldsPage() {
  const { prompt, setPrompt, preview, world, audit, error, isBusy, busyLabel, statusMessage, previewWorld, buildWorld, auditWorld, runFiveMinuteDemo, setActivePage } = useAuditra();
  const active = preview ?? world;
  const facts = active ? [
    ["Market", active.spec.country + " / " + active.spec.currencies.join(" + ")],
    ["Business", active.spec.world_name || active.spec.merchant_name],
    ["Activity", compact(active.spec.record_count) + " orders"],
    ["Payments", active.spec.payment_methods.join(" + ")],
    ["Fee", (Number(active.spec.fee_rate) * 100).toFixed(2) + "%"],
    ["Settlement", "T+" + active.spec.settlement_delay_days],
    ["Refunds", Number(active.spec.refund_rate) > 0 ? "Enabled" : "Off"],
    ["Risk", titleCase(active.spec.anomaly_mode)],
  ] : [];

  return <div className="space-y-7">
    <header className="animate-fade-up border-b border-white/10 pb-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div><StatusPill accent="cyan" dot>Financial World Builder</StatusPill><h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">Create a controlled financial world</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400 sm:text-base">Describe the merchant, let Auditra understand the setup, then generate a validated world ready for audit.</p></div>
        <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-md border border-white/10 bg-white/[0.06] px-4 text-sm font-semibold text-white hover:bg-white/[0.1]" disabled={isBusy} onClick={() => void runFiveMinuteDemo()}><PlayCircle className="h-4 w-4" />Run demo</button>
      </div>
    </header>
    {error ? <InlineError error={error} /> : null}
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_430px]">
      <WorkspacePanel className="animate-fade-up-delayed">
        <SectionTitle icon={<FileText className="h-5 w-5" />} eyebrow="Describe" title="What should Auditra audit?" detail="Use plain language. The model can interpret intent, while deterministic generation stays authoritative." />
        <textarea className="mt-5 min-h-[190px] w-full resize-y rounded-lg border border-white/10 bg-black/25 px-4 py-4 text-sm leading-6 text-white placeholder:text-slate-600" placeholder="Describe the financial world you want to audit..." value={prompt} onChange={(event) => setPrompt(event.target.value)} />
        <div className="mt-4 grid gap-2 lg:grid-cols-3">{PROMPT_SUGGESTIONS.map((item) => <button key={item} type="button" className="rounded-md border border-white/10 bg-white/[0.035] p-3 text-left text-xs leading-5 text-slate-400 hover:border-cyan-400/30 hover:text-cyan-100" onClick={() => setPrompt(item)}>{item}</button>)}</div>
        <div className="mt-5 flex flex-wrap gap-3"><button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-md border border-cyan-400/20 bg-cyan-400/10 px-4 text-sm font-semibold text-cyan-100 hover:bg-cyan-400/15 disabled:opacity-50" disabled={isBusy || !prompt.trim()} onClick={() => void previewWorld()}><Eye className="h-4 w-4" />Understand</button><button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-md bg-gradient-to-r from-indigo-500 via-sky-500 to-cyan-400 px-5 text-sm font-semibold text-white shadow-[0_14px_36px_rgba(14,165,233,0.22)] hover:brightness-110 disabled:opacity-50" disabled={isBusy || !prompt.trim()} onClick={() => void buildWorld()}>{isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}{isBusy ? busyLabel || "Building" : "Build world"}</button></div>
        {isBusy ? <div className="mt-3 text-sm text-cyan-200">{statusMessage}</div> : null}
      </WorkspacePanel>
      <WorkspacePanel className="animate-fade-up-delayed-2">
        <SectionTitle eyebrow="Understand" title={active ? "Financial setup understood" : "Waiting for a world"} detail={active ? "Only the useful summary is shown here. Schema details stay advanced." : "Preview or build to see the interpreted setup."} />
        {active ? <div className="mt-5 grid gap-2 sm:grid-cols-2">{facts.map(([label, value]) => <Fact key={label} label={label} value={value} />)}</div> : <div className="mt-6 rounded-lg border border-dashed border-white/10 p-8 text-center text-sm text-slate-500">No financial world yet.</div>}
        {active ? <details className="mt-5 rounded-lg border border-white/10 bg-black/20 p-4"><summary className="cursor-pointer text-sm font-semibold text-white">View advanced setup details</summary><pre className="mt-4 max-h-[300px] overflow-auto text-xs leading-5 text-slate-400">{JSON.stringify(active.spec, null, 2)}</pre></details> : null}
      </WorkspacePanel>
    </div>
    <WorkspacePanel className="animate-fade-up-delayed"><SectionTitle eyebrow="Build" title={world ? "World ready" : "Build progress"} detail={world ? "The dataset is validated, hidden truth is locked, and the audit can begin." : "Auditra will understand, generate relationships, create transactions, and validate the world."} />
      {world ? <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label="Orders" value={compact(world.summary.orders)} accent="cyan" /><MetricTile label="Payments" value={compact(world.summary.payments)} accent="indigo" /><MetricTile label="Settlements" value={compact(world.summary.settlements)} accent="emerald" /><MetricTile label="Volume" value={money(world.summary.payment_volume)} accent="amber" /></div> : null}
      {world ? <div className="mt-5 flex flex-wrap gap-3"><button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-slate-950 hover:bg-slate-100 disabled:opacity-50" disabled={isBusy} onClick={() => void auditWorld()}><ShieldCheck className="h-4 w-4" />{audit ? "Audit again" : "Audit world"}</button><button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-md border border-white/10 px-4 text-sm font-semibold text-slate-300 hover:bg-white/[0.06]" onClick={() => setActivePage("audits")}>Open audit <ArrowRight className="h-4 w-4" /></button></div> : null}
    </WorkspacePanel>
  </div>;
}

function Fact({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3"><div className="text-[11px] font-semibold text-slate-500">{label}</div><div className="mt-1 text-sm font-semibold text-white">{value}</div></div>; }
