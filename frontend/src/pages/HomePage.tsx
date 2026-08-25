import { ArrowRight, PlayCircle, ShieldAlert, Sparkles, WandSparkles } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Textarea } from "../components/ui/Field";
import { Metric } from "../components/ui/Metric";
import { ErrorState } from "../components/ui/State";
import { compact, money, pct } from "../lib/format";
import { attentionCases, auditHealthLabel, auditHealthRatio, auditHealthTone, caseShortExplanation, caseTitle, potentialExposure } from "../lib/product";
import { riskTone } from "../lib/status";
import { useAuditra, PROMPT_SUGGESTIONS } from "../hooks/useAuditra";

export function HomePage() {
  const {
    prompt,
    setPrompt,
    world,
    audit,
    buildWorld,
    runFiveMinuteDemo,
    setActivePage,
    isBusy,
    error,
  } = useAuditra();

  const greeting = greet();
  const cases = attentionCases(audit);
  const health = auditHealthRatio(audit);
  const exposure = potentialExposure(cases);

  if (!world && !audit) {
    return (
      <div className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_420px]">
          <div className="rounded-[32px] border border-white/70 bg-[linear-gradient(135deg,rgba(99,102,241,0.14),rgba(56,189,248,0.10),rgba(255,255,255,0.96))] p-6 shadow-panel xl:p-8">
            <Badge tone="review">Auditra</Badge>
            <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-5xl">
              Know what&apos;s happening before money becomes a problem.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
              Describe the financial world you want to audit, and Auditra will build it, audit it, and explain what matters in plain language.
            </p>

            <div className="mt-8 rounded-[28px] border border-white/80 bg-white/90 p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)]">
              <div className="text-sm font-semibold text-slate-950">Create a financial world</div>
              <Textarea
                className="mt-4 min-h-[180px] rounded-[24px] border-white bg-slate-50 px-5 py-4 text-base shadow-none"
                placeholder="Describe the financial world you want to audit..."
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  ["E-commerce", PROMPT_SUGGESTIONS[0]],
                  ["Marketplace", PROMPT_SUGGESTIONS[2]],
                  ["Subscription business", PROMPT_SUGGESTIONS[1]],
                  ["High-refund merchant", "Create a merchant with frequent refunds, card settlements, partial captures and fee mismatches."],
                ].map(([label, value]) => (
                  <button key={label} className="rounded-full border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50" onClick={() => setPrompt(value)}>
                    {label}
                  </button>
                ))}
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button variant="primary" icon={<WandSparkles className="h-4 w-4" />} disabled={isBusy || !prompt.trim()} onClick={() => void buildWorld()}>
                  Build world
                </Button>
                <Button icon={<PlayCircle className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>
                  Audit existing data
                </Button>
              </div>
              <div className="mt-3 text-sm text-muted">The secondary action opens the live demo world so you can see the full audit flow immediately.</div>
            </div>
          </div>

          <div className="space-y-4">
            <Card className="rounded-[28px] border-white/80 bg-white/90 p-6">
              <div className="flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
                  <Sparkles className="h-5 w-5" />
                </span>
                <div>
                  <div className="text-sm font-semibold text-slate-950">A simpler audit story</div>
                  <div className="text-sm text-muted">Create, audit, review, and trust without digging through engineering detail.</div>
                </div>
              </div>
              <div className="mt-5 space-y-3">
                {["Describe a financial world", "Let Auditra audit the activity", "Review only what needs attention", "Understand why the result can be trusted"].map((step, index) => (
                  <div key={step} className="flex items-center gap-3 rounded-2xl border border-line bg-slate-50/80 px-4 py-3">
                    <span className="grid h-8 w-8 place-items-center rounded-full bg-white text-sm font-semibold text-slate-950">{index + 1}</span>
                    <span className="text-sm font-medium text-slate-700">{step}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="rounded-[28px] border-white/80 bg-slate-950 p-6 text-white">
              <div className="text-sm font-semibold text-white">What you&apos;ll get</div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <Metric label="Worlds" value="Live" detail="Generated from your prompt" />
                <Metric label="Audits" value="Explained" detail="Clear outcomes with evidence" />
                <Metric label="Review" value="Focused" detail="Only the cases that matter" />
                <Metric label="Insights" value="Trusted" detail="AI value and accuracy in context" />
              </div>
            </Card>
          </div>
        </section>

        {error ? <ErrorState title="Something went wrong" error={error} /> : null}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_380px]">
        <div className="rounded-[32px] border border-white/70 bg-[linear-gradient(135deg,rgba(79,70,229,0.14),rgba(14,165,233,0.10),rgba(255,255,255,0.96))] p-6 shadow-panel xl:p-8">
          <div className="text-sm font-medium text-slate-500">{greeting}</div>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950">Your financial control center</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted">
            Auditra has turned your world into a live audit workspace. Start with the health summary, then move straight into the cases that matter.
          </p>

          <div className="mt-8 rounded-[28px] border border-white/80 bg-white/92 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Audit health</div>
                <div className="mt-2 text-5xl font-semibold tracking-tight text-slate-950">{pct(health, 1)}</div>
                <div className="mt-2 text-base font-medium text-slate-700">{auditHealthLabel(audit)}</div>
                <div className="mt-1 text-sm text-muted">Financial activity reconciled across the current audit.</div>
              </div>
              <Badge tone={auditHealthTone(audit)}>{auditHealthLabel(audit)}</Badge>
            </div>
            <div className="mt-6 h-3 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,#22c55e_0%,#38bdf8_60%,#4f46e5_100%)]"
                style={{ width: `${Math.max(8, Math.min(100, health * 100))}%` }}
              />
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button variant="primary" icon={<ShieldAlert className="h-4 w-4" />} disabled={!cases.length} onClick={() => setActivePage("review")}>
                Review exceptions
              </Button>
              <Button onClick={() => setActivePage("audits")}>Open audit summary</Button>
            </div>
          </div>
        </div>

        <Card className="rounded-[28px] border-white/80 bg-white/90 p-6">
          <div className="text-sm font-semibold text-slate-950">Right now</div>
          <div className="mt-5 space-y-3">
            <Metric label="Reconciled" value={pct(health, 1)} tone="success" />
            <Metric label="Needs attention" value={compact(cases.length)} tone={cases.length ? "warning" : "success"} />
            <Metric label="Financial exposure" value={money(exposure)} tone={exposure ? "warning" : "success"} />
            <Metric label="Audit health" value={auditHealthLabel(audit)} tone={auditHealthTone(audit)} />
          </div>
        </Card>
      </section>

      {cases.length ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-slate-950">Needs your attention</h2>
              <p className="text-sm text-muted">The most important exceptions are surfaced here so you can move directly into review.</p>
            </div>
            <Button onClick={() => setActivePage("review")}>View all</Button>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {cases.slice(0, 3).map((item) => (
              <button key={item.case_id} className="rounded-[28px] border border-white/70 bg-white/90 p-5 text-left shadow-panel transition hover:-translate-y-0.5 hover:shadow-[0_18px_42px_rgba(15,23,42,0.08)]" onClick={() => setActivePage("review")}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="grid h-11 w-11 place-items-center rounded-2xl bg-amber-50 text-amber-600">
                      <ShieldAlert className="h-5 w-5" />
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-slate-950">{caseTitle(item)}</div>
                      <div className="text-sm text-muted">{money(item.decision.financial_impact)} exposure</div>
                    </div>
                  </div>
                  <Badge tone={riskTone(item.risk_score)}>Risk {item.risk_score.toFixed(1)}</Badge>
                </div>
                <p className="mt-4 text-sm leading-6 text-muted">{caseShortExplanation(item)}</p>
                <div className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-indigo-700">
                  Review case
                  <ArrowRight className="h-4 w-4" />
                </div>
              </button>
            ))}
          </div>
        </section>
      ) : (
        <Card className="rounded-[28px] border-emerald-200 bg-emerald-50/80 p-6">
          <div className="text-lg font-semibold text-emerald-900">Everything looks healthy.</div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-800">This audit did not surface urgent exceptions. You can still open Insights for a deeper look at AI value and controller accuracy.</p>
        </Card>
      )}

      {error ? <ErrorState title="Something went wrong" error={error} /> : null}
    </div>
  );
}

function greet() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Welcome back";
}
