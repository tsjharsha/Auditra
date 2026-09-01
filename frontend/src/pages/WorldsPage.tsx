import { ArrowRight, CheckCircle2, Eye, FileText, PlayCircle, RefreshCw, ShieldCheck, Upload, WandSparkles } from "lucide-react";
import { useState } from "react";
import { auditraApi } from "../api/client";
import { InlineError, MetricTile, SectionTitle, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { PROMPT_SUGGESTIONS, useAuditra } from "../hooks/useAuditra";
import { compact, money, titleCase } from "../lib/format";
import type { IngestionResult } from "../types/auditra";

const samplePayload = JSON.stringify({
  merchants: [{ merchant_id: "MCH_DEMO", name: "Demo Merchant" }],
  orders: [{ order_id: "ORD_001", merchant_id: "MCH_DEMO", customer_id: "CUS_001", amount: "2500.00", currency: "INR" }],
  payments: [{ payment_id: "PAY_001", order_id: "ORD_001", merchant_id: "MCH_DEMO", customer_id: "CUS_001", amount: "2500.00", currency: "INR", payment_method: "upi" }],
  settlements: [{ settlement_id: "SET_001", payment_id: "PAY_001", merchant_id: "MCH_DEMO", amount: "2447.00", currency: "INR", batch_id: "BATCH_001" }],
}, null, 2);

export function WorldsPage() {
  const { prompt, setPrompt, preview, world, audit, error, isBusy, busyLabel, statusMessage, previewWorld, buildWorld, auditWorld, runFiveMinuteDemo, setActivePage } = useAuditra();
  const [adapter, setAdapter] = useState<"json" | "razorpay_test">("json");
  const [importText, setImportText] = useState(samplePayload);
  const [ingestion, setIngestion] = useState<IngestionResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const active = preview ?? world;
  const facts = active ? [
    ["Market", active.spec.country + " / " + active.spec.currencies.join(" + ")],
    ["Business", active.spec.world_name || active.spec.merchant_name],
    ["Activity", compact(active.spec.record_count) + " orders"],
    ["Payments", active.spec.payment_methods.join(" + ")],
    ["Settlement", "T+" + active.spec.settlement_delay_days],
    ["Risk", titleCase(active.spec.anomaly_mode)],
  ] : [];

  async function validateImport() {
    setImportError(null);
    setIngestion(null);
    setImporting(true);
    try {
      const payload = JSON.parse(importText) as Record<string, unknown>;
      setIngestion(await auditraApi.ingest(adapter, payload));
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "The batch could not be parsed.");
    } finally {
      setImporting(false);
    }
  }

  return <div className="space-y-6 pb-8">
    <header className="rise-in border-b border-white/10 pb-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div><StatusPill accent="cyan" dot>Batch workspace</StatusPill><h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">Prepare the batch before the close.</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-[#9a9792] sm:text-base">Generate a measurable finance-operations scenario, or validate the shape of an external test batch before connecting it to a production adapter.</p></div>
        <button type="button" className="button-secondary" disabled={isBusy} onClick={() => void runFiveMinuteDemo()}><PlayCircle className="h-4 w-4" />Run demo</button>
      </div>
    </header>

    {error ? <InlineError error={error} /> : null}

    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <WorkspacePanel>
        <SectionTitle icon={<FileText className="h-5 w-5" />} eyebrow="Generate" title="Create a controlled scenario" detail="Use plain language for setup. The generated batch includes locked hidden truth so the close can be measured afterwards." />
        <textarea className="mt-5 min-h-[170px] w-full resize-y rounded-lg border border-white/10 bg-black/20 px-4 py-4 text-sm leading-6 text-white placeholder:text-[#77736e]" placeholder="Describe the financial batch..." value={prompt} onChange={(event) => setPrompt(event.target.value)} />
        <div className="mt-4 grid gap-2 lg:grid-cols-3">{PROMPT_SUGGESTIONS.map((item) => <button key={item} type="button" className="rounded-md border border-white/10 bg-white/[0.025] p-3 text-left text-xs leading-5 text-[#9a9792] hover:border-[#c7ff54]/40 hover:text-white" onClick={() => setPrompt(item)}>{item}</button>)}</div>
        <div className="mt-5 flex flex-wrap gap-3"><button type="button" className="button-secondary" disabled={isBusy || !prompt.trim()} onClick={() => void previewWorld()}><Eye className="h-4 w-4" />Understand</button><button type="button" className="button-primary" disabled={isBusy || !prompt.trim()} onClick={() => void buildWorld()}>{isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}{isBusy ? busyLabel || "Building" : "Build scenario"}</button></div>
        {isBusy ? <div className="mt-3 text-sm text-[#d6ff82]">{statusMessage}</div> : null}
      </WorkspacePanel>

      <WorkspacePanel>
        <SectionTitle eyebrow="Summary" title={active ? "Scenario ready" : "Waiting for a batch"} detail={active ? "The operational facts that matter before the controller runs." : "Build or preview a scenario to see its close configuration."} />
        {active ? <div className="mt-5 grid gap-2 sm:grid-cols-2">{facts.map(([label, value]) => <Fact key={label} label={label} value={value} />)}</div> : <div className="mt-6 rounded-lg border border-dashed border-white/10 p-8 text-center text-sm text-[#77736e]">No scenario yet.</div>}
        {active ? <details className="mt-5 rounded-lg border border-white/10 bg-black/20 p-4"><summary className="cursor-pointer text-sm font-semibold text-white">View technical setup</summary><pre className="mt-4 max-h-[260px] overflow-auto text-xs leading-5 text-[#9a9792]">{JSON.stringify(active.spec, null, 2)}</pre></details> : null}
      </WorkspacePanel>
    </div>

    <WorkspacePanel>
      <SectionTitle icon={<Upload className="h-5 w-5" />} eyebrow="Import test data" title="Validate an external batch shape" detail="JSON and Razorpay-style test payloads are normalized through the same canonical schema. Imported data is validated but is not presented as a hidden-truth benchmark." />
      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div><div className="mb-3 flex flex-wrap gap-2"><button type="button" className={"record-option px-4 " + (adapter === "json" ? "record-option-active" : "")} onClick={() => setAdapter("json")}>Canonical JSON</button><button type="button" className={"record-option px-4 " + (adapter === "razorpay_test" ? "record-option-active" : "")} onClick={() => setAdapter("razorpay_test")}>Razorpay-style JSON</button></div><textarea className="min-h-[220px] w-full resize-y rounded-lg border border-white/10 bg-black/20 p-4 font-mono text-xs leading-5 text-[#c7c4bf]" value={importText} onChange={(event) => setImportText(event.target.value)} /><button type="button" className="button-secondary mt-4" disabled={importing} onClick={() => void validateImport()}>{importing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}{importing ? "Validating" : "Validate batch"}</button>{importError ? <div className="mt-3 text-sm text-[#ffb08d]">{importError}</div> : null}</div>
        <div className="rounded-lg border border-white/10 bg-black/15 p-4">{ingestion ? <><div className="section-kicker">Normalized</div><div className="mt-2 text-lg font-semibold text-white">Batch accepted</div><div className="mt-5 space-y-3">{Object.entries(ingestion.rows_loaded).map(([label, value]) => <div key={label} className="flex justify-between text-sm"><span className="text-[#9a9792]">{titleCase(label)}</span><span className="font-semibold text-white">{compact(value)}</span></div>)}</div><p className="mt-5 text-xs leading-5 text-[#77736e]">Use a controlled scenario for hidden-truth accuracy and assurance. External data retains the same adapter boundary for a later production integration.</p></> : <><div className="section-kicker">Adapter boundary</div><p className="mt-3 text-sm leading-6 text-[#9a9792]">The importer accepts payments, orders, settlements, refunds, fees, and merchants, then validates references and finance data types before controller integration.</p></>}</div>
      </div>
    </WorkspacePanel>

    <WorkspacePanel><SectionTitle eyebrow="Ready to close" title={world ? "Scenario is ready" : "Build progress"} detail={world ? "The dataset is validated, hidden truth is locked, and the audit can begin." : "A controlled scenario is the measurable path for the five-minute demo."} />
      {world ? <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label="Orders" value={compact(world.summary.orders)} accent="cyan" /><MetricTile label="Payments" value={compact(world.summary.payments)} accent="indigo" /><MetricTile label="Settlements" value={compact(world.summary.settlements)} accent="emerald" /><MetricTile label="Volume" value={money(world.summary.payment_volume)} accent="amber" /></div> : null}
      {world ? <div className="mt-5 flex flex-wrap gap-3"><button type="button" className="button-primary" disabled={isBusy} onClick={() => void auditWorld()}><ShieldCheck className="h-4 w-4" />{audit ? "Audit again" : "Run audit"}</button><button type="button" className="button-quiet" onClick={() => setActivePage("audits")}>Open audit <ArrowRight className="h-4 w-4" /></button></div> : null}
    </WorkspacePanel>
  </div>;
}

function Fact({ label, value }: { label: string; value: string }) { return <div className="fact-box"><div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#77736e]">{label}</div><div className="mt-2 text-sm font-semibold text-white">{value}</div></div>; }
