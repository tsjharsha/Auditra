import {
  ArrowRight,
  Banknote,
  Check,
  CircleAlert,
  Database,
  Fingerprint,
  FlaskConical,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { InlineError, MetricTile, StatusPill, WorkspacePanel } from "../components/WorkspaceUI";
import { useAuditra } from "../hooks/useAuditra";
import { compact, money, titleCase } from "../lib/format";
import { cn } from "../lib/utils";
import type { ChallengeDefinition } from "../types/auditra";

const story = ["Generate", "Close", "Verify", "Challenge", "Assure"];

export function HomePage() {
  const {
    challenges,
    selectedChallengeId,
    setSelectedChallengeId,
    world,
    seed,
    setSeed,
    buildChallenge,
    setActivePage,
    isBusy,
    busyLabel,
    statusMessage,
    error,
  } = useAuditra();
  const selected = challenges.find((item) => item.challenge_id === selectedChallengeId) ?? challenges[0];
  const currentMatches = world?.challenge?.challenge_id === selectedChallengeId;

  return (
    <div className="space-y-7">
      <section className="animate-fade-up border-b border-white/10 pb-7">
        <div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-4xl">
            <StatusPill accent="cyan" dot>Autonomous finance assurance lab</StatusPill>
            <h1 className="mt-5 max-w-4xl text-4xl font-semibold leading-tight text-white sm:text-5xl">
              Would you let this AI close a real settlement batch?
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-400">
              Generate a complete payment world with hidden ground truth, then prove exactly where an AI finance controller is safe, uncertain, or wrong.
            </p>
          </div>
          <div className="grid min-w-[280px] grid-cols-5 gap-1 rounded-lg border border-white/10 bg-white/[0.035] p-2">
            {story.map((stage, index) => (
              <div key={stage} className="text-center">
                <span className="mx-auto grid h-7 w-7 place-items-center rounded-md bg-cyan-400/10 text-xs font-semibold text-cyan-200">{index + 1}</span>
                <span className="mt-1.5 block text-[10px] text-slate-500">{stage}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="animate-fade-up-delayed">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <div className="text-xs font-semibold text-cyan-300">Scenario lab</div>
            <h2 className="mt-1 text-xl font-semibold text-white">Choose the risk to prove</h2>
          </div>
          <div className="hidden text-xs text-slate-500 sm:block">One immutable seed. Repeatable results.</div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {challenges.map((challenge) => (
            <ChallengeCard
              key={challenge.challenge_id}
              challenge={challenge}
              active={challenge.challenge_id === selectedChallengeId}
              onSelect={() => setSelectedChallengeId(challenge.challenge_id)}
            />
          ))}
          {!challenges.length ? <CatalogSkeleton /> : null}
        </div>
      </section>

      {selected ? (
        <WorkspacePanel className="animate-fade-up-delayed-2 overflow-hidden">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-center">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill accent={selected.accent}>{selected.anomaly_mode} controls</StatusPill>
                {selected.recommended ? <StatusPill accent="emerald"><Sparkles className="h-3.5 w-3.5" /> Buildathon pick</StatusPill> : null}
              </div>
              <h2 className="mt-5 text-2xl font-semibold text-white">{selected.name}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{selected.description}</p>
              <div className="mt-5 flex items-start gap-3 rounded-lg border border-amber-400/15 bg-amber-400/[0.06] p-4">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                <div>
                  <div className="text-xs font-semibold text-amber-200">Risk under test</div>
                  <p className="mt-1 text-sm leading-6 text-slate-400">{selected.risk}</p>
                </div>
              </div>
              <div className="mt-6 flex flex-wrap items-end gap-3">
                <label className="block">
                  <span className="mb-1.5 block text-xs text-slate-500">Reproducible seed</span>
                  <input
                    className="h-11 w-28 rounded-lg border border-white/10 bg-slate-950/80 px-3 text-sm text-white"
                    type="number"
                    value={seed}
                    onChange={(event) => setSeed(Number(event.target.value) || 42)}
                  />
                </label>
                <button
                  type="button"
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 via-sky-500 to-cyan-400 px-5 text-sm font-semibold text-white shadow-[0_14px_36px_rgba(14,165,233,0.22)] transition hover:brightness-110 disabled:opacity-50"
                  disabled={isBusy}
                  onClick={() => void buildChallenge()}
                >
                  {isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                  {isBusy ? busyLabel || "Generating" : "Generate financial batch"}
                </button>
              </div>
              {isBusy ? <p className="mt-3 text-sm text-cyan-200">{statusMessage}</p> : null}
            </div>
            <dl className="divide-y divide-white/[0.07] border-y border-white/10">
              <SpecRow icon={<Database />} label="Transactions" value={compact(selected.record_count)} />
              <SpecRow icon={<Banknote />} label="Settlement" value="INR / T+2" />
              <SpecRow icon={<Fingerprint />} label="Anomalies" value={titleCase(selected.anomaly_mode)} />
              <SpecRow icon={<LockKeyhole />} label="Ground truth" value="Hidden until verification" />
            </dl>
          </div>
        </WorkspacePanel>
      ) : null}

      {error ? <InlineError error={error} /> : null}
      {world && currentMatches ? <BatchReady /> : null}
    </div>
  );
}

function ChallengeCard({
  challenge,
  active,
  onSelect,
}: {
  challenge: ChallengeDefinition;
  active: boolean;
  onSelect: () => void;
}) {
  const icons = {
    "settlement-reconciliation": <ShieldCheck className="h-5 w-5" />,
    "refund-integrity": <Fingerprint className="h-5 w-5" />,
    "fee-leakage": <Banknote className="h-5 w-5" />,
    "black-swan-close": <FlaskConical className="h-5 w-5" />,
  };
  const tones = {
    cyan: "border-cyan-400/35 bg-cyan-400/[0.08] text-cyan-200",
    rose: "border-rose-400/35 bg-rose-400/[0.08] text-rose-200",
    amber: "border-amber-400/35 bg-amber-400/[0.08] text-amber-200",
    indigo: "border-indigo-400/35 bg-indigo-400/[0.08] text-indigo-200",
  };
  return (
    <button
      type="button"
      className={cn(
        "relative min-h-[190px] rounded-lg border p-5 text-left transition duration-300",
        active
          ? cn(tones[challenge.accent], "shadow-[0_16px_46px_rgba(8,145,178,0.12)]")
          : "border-white/10 bg-white/[0.035] text-slate-300 hover:border-white/20 hover:bg-white/[0.055]",
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-3">
        <span className={cn("grid h-10 w-10 place-items-center rounded-lg border", active ? "border-current/20 bg-black/10" : "border-white/10 bg-white/5")}>
          {icons[challenge.challenge_id as keyof typeof icons] ?? <FlaskConical className="h-5 w-5" />}
        </span>
        {active ? <span className="grid h-6 w-6 place-items-center rounded-full bg-white text-slate-950"><Check className="h-3.5 w-3.5" /></span> : null}
      </div>
      <div className="mt-5 text-base font-semibold text-white">{challenge.name}</div>
      <p className="mt-2 text-xs leading-5 text-slate-500">{challenge.description}</p>
      <div className="mt-4 text-[11px] font-semibold uppercase text-current">{titleCase(challenge.anomaly_mode)}</div>
    </button>
  );
}

function CatalogSkeleton() {
  return (
    <div className="col-span-full grid min-h-[190px] place-items-center rounded-lg border border-dashed border-white/10 text-sm text-slate-500">
      Loading enterprise challenge catalog...
    </div>
  );
}

function SpecRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 py-3.5 text-sm">
      <span className="text-slate-600 [&>svg]:h-4 [&>svg]:w-4">{icon}</span>
      <dt className="text-slate-500">{label}</dt>
      <dd className="ml-auto text-right font-semibold text-white">{value}</dd>
    </div>
  );
}

function BatchReady() {
  const { world, setActivePage } = useAuditra();
  if (!world) return null;
  return (
    <section className="animate-scale-in overflow-hidden rounded-lg border border-emerald-400/25 bg-emerald-400/[0.06]">
      <div className="border-b border-emerald-400/15 px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-300 text-emerald-950"><Check className="h-5 w-5" /></span>
            <div>
              <div className="font-semibold text-white">Challenge batch ready</div>
              <div className="mt-0.5 text-xs text-emerald-200/70">{world.world_id} / seed {world.spec.seed}</div>
            </div>
          </div>
          <button
            type="button"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"
            onClick={() => setActivePage("audits")}
          >
            Let the controller close it
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4 sm:p-6">
        <MetricTile label="Payment volume" value={money(world.summary.payment_volume)} detail="Synthetic INR volume" icon={<Banknote className="h-4 w-4" />} accent="cyan" />
        <MetricTile label="Payments" value={compact(world.summary.payments)} detail={compact(world.summary.settlements) + " settlements"} icon={<Database className="h-4 w-4" />} accent="indigo" />
        <MetricTile label="Exceptions planted" value={compact(world.summary.anomalies)} detail="Unknown to the controller" icon={<Fingerprint className="h-4 w-4" />} accent="amber" />
        <MetricTile label="Ground truth" value="Locked" detail={compact(world.ground_truth?.records ?? world.summary.payments) + " labels withheld"} icon={<LockKeyhole className="h-4 w-4" />} accent="emerald" />
      </div>
    </section>
  );
}
