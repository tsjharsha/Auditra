import { Boxes, PlayCircle, ShieldCheck, Workflow } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { Field, Input, Textarea } from "../components/ui/Field";
import { Metric, MetricGrid } from "../components/ui/Metric";
import { ErrorState } from "../components/ui/State";
import { BuilderPipeline } from "../features/world/BuilderPipeline";
import { compact, money, pct } from "../lib/format";
import { useAuditra, PROMPT_SUGGESTIONS } from "../hooks/useAuditra";

export function HomePage() {
  const {
    prompt,
    setPrompt,
    seed,
    setSeed,
    preview,
    world,
    audit,
    buildWorld,
    runFiveMinuteDemo,
    setActivePage,
    isBusy,
    error,
  } = useAuditra();

  return (
    <div className="space-y-5">
      <section className="grid gap-5 rounded-lg border border-line bg-white p-5 shadow-panel xl:grid-cols-[minmax(0,1fr)_440px]">
        <div className="min-w-0">
          <div className="mb-4 inline-flex min-h-7 items-center rounded-full border border-teal/20 bg-teal/10 px-3 text-xs font-bold uppercase text-teal">
            AUDITRA
          </div>
          <h1 className="max-w-4xl text-4xl font-black uppercase leading-tight text-ink md:text-5xl">
            FROM FINANCIAL INTENT TO VERIFIED CONTROL.
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-muted">
            Describe the merchant world, generate source records, audit every transaction, investigate exceptions, verify evidence, and measure the controller against hidden ground truth.
          </p>
          <div className="mt-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_160px]">
            <Field label="Financial Intent">
              <Textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
            </Field>
            <Field label="Seed">
              <Input type="number" min={1} value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
            </Field>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="primary" icon={<Workflow className="h-4 w-4" />} disabled={isBusy} onClick={() => void buildWorld()}>
              Build Financial World
            </Button>
            <Button icon={<PlayCircle className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>
              Use Demo World
            </Button>
            <Button icon={<Boxes className="h-4 w-4" />} onClick={() => setActivePage("world-builder")}>
              World Builder
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {PROMPT_SUGGESTIONS.map((item) => (
              <button
                key={item}
                className="max-w-full truncate rounded-lg border border-line bg-slate-50 px-3 py-2 text-left text-xs font-semibold text-steel hover:bg-white"
                onClick={() => setPrompt(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <Card className="self-start">
          <SectionHeader title="Current Run" kicker={world ? world.world_id : "No active world"} />
          <div className="space-y-3">
            <Metric label="Records" value={world ? compact(world.summary.payments) : "Pending"} />
            <Metric label="Payment Volume" value={world ? money(world.summary.payment_volume) : "Pending"} />
            <Metric label="Controller Accuracy" value={audit ? pct(audit.evaluation.metrics.accuracy) : "Pending"} tone={audit ? "success" : "default"} />
            <Metric label="Exceptions" value={audit ? audit.controller_run.cases.filter((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status)).length : "Pending"} />
            <Button className="w-full" icon={<ShieldCheck className="h-4 w-4" />} disabled={!audit} onClick={() => setActivePage("reconciliation")}>
              Open Reconciliation
            </Button>
          </div>
        </Card>
      </section>

      {error ? <ErrorState title="Auditra request failed" error={error} /> : null}

      <BuilderPipeline preview={preview} world={world} audit={audit} isBusy={isBusy} />

      <MetricGrid>
        <Metric label="World" value={world?.world_id ?? "Not built"} detail={world?.summary.merchant} />
        <Metric label="Dataset" value={world?.dataset_id ?? "Not built"} />
        <Metric label="Validation" value={world?.validation.valid ? "Passed" : "Pending"} tone={world?.validation.valid ? "success" : "default"} />
        <Metric label="AI Calls" value={audit?.controller_run.metrics.llm_calls ?? "Pending"} />
        <Metric label="Human Review" value={audit ? pct(audit.controller_run.metrics.human_review_rate) : "Pending"} tone={audit?.controller_run.metrics.human_review_rate ? "review" : "default"} />
        <Metric label="Survival" value={audit?.survival_status ?? "Pending"} tone={audit ? (audit.evaluation.failures.length ? "warning" : "success") : "default"} />
      </MetricGrid>
    </div>
  );
}
