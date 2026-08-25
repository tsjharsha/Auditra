import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Eye, Hammer, PlayCircle, ShieldCheck, WandSparkles } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { Textarea } from "../components/ui/Field";
import { ErrorState, EmptyState, SuccessState } from "../components/ui/State";
import { AuditProgress } from "../features/audit/AuditProgress";
import { SchemaRelationshipFlow } from "../features/graph/RelationshipFlow";
import { BuilderPipeline } from "../features/world/BuilderPipeline";
import { SchemaBrowser } from "../features/world/SchemaBrowser";
import { SpecEditor } from "../features/world/SpecEditor";
import { WorldRecordExplorer } from "../features/world/WorldRecordExplorer";
import { compact, money } from "../lib/format";
import { useAuditra, PROMPT_SUGGESTIONS } from "../hooks/useAuditra";

type WorldStep = "describe" | "review" | "build" | "audit" | "explore";

const steps: Array<{ id: WorldStep; label: string }> = [
  { id: "describe", label: "Describe" },
  { id: "review", label: "Review" },
  { id: "build", label: "Build" },
  { id: "audit", label: "Audit" },
  { id: "explore", label: "Explore" },
];

export function WorldsPage() {
  const {
    prompt,
    setPrompt,
    preview,
    world,
    audit,
    error,
    isBusy,
    statusMessage,
    previewWorld,
    buildWorld,
    buildWorldFromSpec,
    auditWorld,
    runFiveMinuteDemo,
    setActivePage,
    selectCase,
  } = useAuditra();
  const activePreview = preview ?? world;
  const defaultStep: WorldStep = audit ? "explore" : world ? "audit" : activePreview ? "review" : "describe";
  const [step, setStep] = useState<WorldStep>(defaultStep);

  useEffect(() => {
    setStep(defaultStep);
  }, [defaultStep]);

  const summaryRows = useMemo(
    () =>
      activePreview
        ? [
            ["Business", activePreview.spec.world_name || activePreview.spec.merchant_name],
            ["Country", activePreview.spec.country],
            ["Currency", activePreview.spec.currencies.join(" / ")],
            ["Orders", compact(activePreview.spec.record_count)],
            ["Payments", activePreview.spec.payment_methods.join(" + ")],
            ["Fee", `${Number(activePreview.spec.fee_rate) * 100}% fee`],
            ["Settlement", `T+${activePreview.spec.settlement_delay_days}`],
            ["Refunds", Number(activePreview.spec.refund_rate) > 0 ? "Enabled" : "Not included"],
          ]
        : [],
    [activePreview],
  );

  return (
    <div className="space-y-6">
      <Card className="rounded-[32px] border-white/70 bg-white/90 p-6 shadow-panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Badge tone="review">Create / Audit / Trust</Badge>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">Build a financial world in a guided flow</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
              Start with a description, review what Auditra understood, build the world, then move directly into audit and exploration.
            </p>
          </div>
          <Button icon={<PlayCircle className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>
            Open demo
          </Button>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-5">
          {steps.map((item, index) => {
            const active = step === item.id;
            const complete = steps.findIndex((entry) => entry.id === defaultStep) >= index;
            return (
              <button
                key={item.id}
                className={`rounded-[24px] border px-4 py-4 text-left transition ${
                  active
                    ? "border-indigo-200 bg-indigo-50/80"
                    : complete
                      ? "border-emerald-200 bg-emerald-50/70"
                      : "border-line bg-slate-50/70 hover:bg-white"
                }`}
                onClick={() => setStep(item.id)}
              >
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Step {index + 1}</div>
                <div className="mt-2 text-sm font-semibold text-slate-950">{item.label}</div>
              </button>
            );
          })}
        </div>
      </Card>

      {error ? <ErrorState title="Something went wrong" error={error} /> : null}

      {step === "describe" ? (
        <Card className="rounded-[32px] border-white/70 bg-[linear-gradient(135deg,rgba(79,70,229,0.10),rgba(14,165,233,0.08),rgba(255,255,255,0.96))] p-6">
          <SectionHeader title="Describe your financial world" kicker="Start with a natural-language prompt. Auditra will turn it into a clean financial setup." />
          <Textarea
            className="min-h-[180px] rounded-[24px] border-white bg-white/90 px-5 py-4 text-base shadow-none"
            placeholder="Describe the financial world you want to audit..."
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
          <div className="mt-4 flex flex-wrap gap-2">
            {PROMPT_SUGGESTIONS.map((item) => (
              <button key={item} className="rounded-full border border-white/90 bg-white/90 px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-white" onClick={() => setPrompt(item)}>
                {item}
              </button>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button icon={<Eye className="h-4 w-4" />} disabled={isBusy || !prompt.trim()} onClick={() => void previewWorld()}>
              Review setup
            </Button>
            <Button variant="primary" icon={<WandSparkles className="h-4 w-4" />} disabled={isBusy || !prompt.trim()} onClick={() => void buildWorld()}>
              Build world
            </Button>
          </div>
        </Card>
      ) : null}

      {step === "review" ? (
        activePreview ? (
          <div className="space-y-4">
            <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
              <SectionHeader title="You described..." kicker="A clean summary of the world Auditra is about to build" />
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {summaryRows.map(([label, value]) => (
                  <div key={label} className="rounded-2xl border border-line bg-slate-50/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
                    <div className="mt-2 text-sm font-semibold text-slate-950">{value}</div>
                  </div>
                ))}
              </div>
              <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                <div className="rounded-[28px] border border-indigo-100 bg-[linear-gradient(135deg,rgba(224,231,255,0.80),rgba(239,246,255,0.92))] p-5">
                  <div className="text-sm font-semibold text-slate-950">Core relationships</div>
                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <FlowPill label="Orders" />
                    <ArrowRight className="h-4 w-4 text-slate-400" />
                    <FlowPill label="Payments" />
                    <ArrowRight className="h-4 w-4 text-slate-400" />
                    <FlowPill label="Settlements" />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge tone="info">Refunds</Badge>
                    <Badge tone="info">Fees</Badge>
                  </div>
                </div>
                <div className="rounded-[28px] border border-line bg-slate-50/80 p-5">
                  <div className="text-sm font-semibold text-slate-950">What happens next</div>
                  <div className="mt-3 text-sm leading-6 text-muted">
                    Auditra will generate transactions, validate the world, and prepare it for audit. You can keep this summary simple or open advanced details if you want to fine-tune the spec.
                  </div>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button onClick={() => setStep("describe")}>Edit</Button>
                <Button variant="primary" icon={<Hammer className="h-4 w-4" />} disabled={isBusy} onClick={() => void buildWorld()}>
                  Build world
                </Button>
              </div>
            </Card>

            <details className="rounded-[32px] border border-white/70 bg-white/90 p-6 shadow-panel">
              <summary className="cursor-pointer text-sm font-semibold text-slate-950">View advanced setup details</summary>
              <div className="mt-5 space-y-5">
                <SpecEditor spec={activePreview.spec} disabled={isBusy} onGenerate={(spec) => void buildWorldFromSpec(spec)} />
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_520px]">
                  <SchemaBrowser schema={activePreview.schema_preview} />
                  <SchemaRelationshipFlow model={activePreview.relationship_model} />
                </div>
              </div>
            </details>
          </div>
        ) : (
          <EmptyState title="Nothing to review yet" detail="Describe a financial world first so Auditra can summarize it back to you." />
        )
      ) : null}

      {step === "build" ? (
        <div className="space-y-4">
          <BuilderPipeline preview={preview} world={world} audit={audit} isBusy={isBusy} />
          {world ? (
            <SuccessState title="Your financial world is ready" detail={`${compact(world.summary.orders)} orders, ${compact(world.summary.payments)} payments, ${compact(world.summary.settlements)} settlements, ${money(world.summary.payment_volume)} financial activity.`} />
          ) : (
            <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
              <div className="text-lg font-semibold text-slate-950">Building in progress</div>
              <p className="mt-2 text-sm leading-6 text-muted">Auditra is understanding your request, generating realistic transactions, validating the world, and getting it ready for audit.</p>
              <div className="mt-3 text-sm font-medium text-indigo-700">{statusMessage}</div>
            </Card>
          )}
          {world ? (
            <div className="flex flex-wrap gap-3">
              <Button variant="primary" icon={<ShieldCheck className="h-4 w-4" />} disabled={isBusy} onClick={() => void auditWorld()}>
                Audit this world
              </Button>
              <Button onClick={() => setStep("explore")}>Explore world</Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {step === "audit" ? (
        world ? (
          <div className="space-y-4">
            <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
              <SectionHeader title="Auditra is checking your financial world" kicker="A clean audit experience that focuses on progress rather than internal system detail" />
              <AuditProgress audit={audit} running={isBusy} />
              <div className="mt-5 flex flex-wrap gap-3">
                <Button variant="primary" icon={<ShieldCheck className="h-4 w-4" />} disabled={isBusy} onClick={() => void auditWorld()}>
                  {audit ? "Run again" : "Audit this world"}
                </Button>
                {audit ? <Button onClick={() => setActivePage("audits")}>Open audit results</Button> : null}
              </div>
            </Card>
            {audit ? <SuccessState title="Audit complete" detail="Auditra finished reconciling this world and prepared a review-ready result." /> : null}
          </div>
        ) : (
          <EmptyState title="Build a world first" detail="Auditra needs a generated financial world before it can run the audit flow." />
        )
      ) : null}

      {step === "explore" ? (
        world ? (
          <WorldRecordExplorer
            world={world}
            cases={audit?.controller_run.cases}
            onSelectCase={(caseId) => {
              selectCase(caseId);
              setActivePage("review");
            }}
          />
        ) : (
          <EmptyState title="No world to explore" detail="Build a world first, then come back here to inspect activity, relationships, and exceptions." />
        )
      ) : null}
    </div>
  );
}

function FlowPill({ label }: { label: string }) {
  return <div className="rounded-full border border-white/90 bg-white/90 px-4 py-2 text-sm font-semibold text-slate-800">{label}</div>;
}
