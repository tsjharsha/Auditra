import { AlertTriangle, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export type Accent = "cyan" | "indigo" | "emerald" | "amber" | "rose" | "slate";

const accentStyles: Record<Accent, { icon: string; value: string; bar: string; pill: string }> = {
  cyan: {
    icon: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
    value: "text-cyan-200",
    bar: "from-cyan-400 to-sky-500",
    pill: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200",
  },
  indigo: {
    icon: "border-indigo-400/20 bg-indigo-400/10 text-indigo-300",
    value: "text-indigo-200",
    bar: "from-indigo-400 to-violet-500",
    pill: "border-indigo-400/20 bg-indigo-400/10 text-indigo-200",
  },
  emerald: {
    icon: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    value: "text-emerald-200",
    bar: "from-emerald-400 to-teal-500",
    pill: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  },
  amber: {
    icon: "border-amber-400/20 bg-amber-400/10 text-amber-300",
    value: "text-amber-200",
    bar: "from-amber-300 to-orange-500",
    pill: "border-amber-400/20 bg-amber-400/10 text-amber-200",
  },
  rose: {
    icon: "border-rose-400/20 bg-rose-400/10 text-rose-300",
    value: "text-rose-200",
    bar: "from-rose-400 to-pink-500",
    pill: "border-rose-400/20 bg-rose-400/10 text-rose-200",
  },
  slate: {
    icon: "border-white/10 bg-white/5 text-slate-300",
    value: "text-white",
    bar: "from-slate-300 to-slate-500",
    pill: "border-white/10 bg-white/5 text-slate-300",
  },
};

export function WorkspacePanel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={cn(
        "rounded-lg border border-white/10 bg-slate-900/70 p-5 shadow-[0_18px_55px_rgba(2,6,23,0.24)] backdrop-blur-xl sm:p-6",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function SectionTitle({
  icon,
  eyebrow,
  title,
  detail,
  action,
}: {
  icon?: ReactNode;
  eyebrow?: string;
  title: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 gap-3">
        {icon ? <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">{icon}</span> : null}
        <div className="min-w-0">
          {eyebrow ? <div className="text-xs font-semibold text-cyan-300">{eyebrow}</div> : null}
          <h2 className="mt-1 text-lg font-semibold text-white sm:text-xl">{title}</h2>
          {detail ? <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-400">{detail}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function MetricTile({
  label,
  value,
  detail,
  icon,
  accent = "slate",
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  icon?: ReactNode;
  accent?: Accent;
}) {
  const style = accentStyles[accent];
  return (
    <div className="min-h-[132px] rounded-lg border border-white/10 bg-white/[0.045] p-4 transition duration-300 hover:border-white/20 hover:bg-white/[0.065]">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-medium text-slate-400">{label}</div>
        {icon ? <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-md border", style.icon)}>{icon}</span> : null}
      </div>
      <div className={cn("mt-4 break-words text-2xl font-semibold", style.value)}>{value}</div>
      {detail ? <div className="mt-2 text-xs leading-5 text-slate-500">{detail}</div> : null}
    </div>
  );
}

export function StatusPill({ children, accent = "slate", dot = false }: { children: ReactNode; accent?: Accent; dot?: boolean }) {
  return (
    <span className={cn("inline-flex min-h-7 items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold", accentStyles[accent].pill)}>
      {dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}

export function SegmentedTabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: T; label: string; count?: number; icon?: ReactNode }>;
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="flex max-w-full gap-1 overflow-x-auto rounded-lg border border-white/10 bg-black/20 p-1" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          className={cn(
            "inline-flex min-h-10 min-w-max items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition",
            active === tab.id ? "bg-white text-slate-950 shadow-sm" : "text-slate-400 hover:bg-white/5 hover:text-white",
          )}
          onClick={() => onChange(tab.id)}
        >
          {tab.icon}
          {tab.label}
          {tab.count !== undefined ? (
            <span className={cn("rounded-full px-1.5 py-0.5 text-[11px]", active === tab.id ? "bg-slate-200 text-slate-700" : "bg-white/10 text-slate-300")}>
              {tab.count}
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

export function InlineError({ error, title = "Auditra could not complete this step" }: { error: unknown; title?: string }) {
  const detail = error instanceof Error ? error.message : String(error ?? "Unknown error");
  return (
    <div className="rounded-lg border border-rose-400/20 bg-rose-400/10 p-4 text-rose-100">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" />
        <div className="min-w-0">
          <div className="text-sm font-semibold">{title}</div>
          <details className="mt-2 text-sm text-rose-200/75">
            <summary className="cursor-pointer">Technical details</summary>
            <p className="mt-2 break-words leading-6">{detail}</p>
          </details>
        </div>
      </div>
    </div>
  );
}

export function BusyOverlay({ label }: { label: string }) {
  return (
    <div className="absolute inset-0 z-20 grid place-items-center rounded-lg bg-slate-950/80 p-6 text-center backdrop-blur-sm">
      <div>
        <LoaderCircle className="mx-auto h-8 w-8 animate-spin text-cyan-300" />
        <div className="mt-3 text-sm font-semibold text-white">{label}</div>
        <div className="mt-1 text-xs text-slate-400">This usually takes a few seconds.</div>
      </div>
    </div>
  );
}

export function ProgressBar({ value, accent = "cyan" }: { value: number; accent?: Accent }) {
  const width = `${Math.max(3, Math.min(100, value * 100))}%`;
  return (
    <div className="h-2 overflow-hidden rounded-full bg-white/10">
      <div className={cn("h-full rounded-full bg-gradient-to-r transition-[width] duration-700", accentStyles[accent].bar)} style={{ width }} />
    </div>
  );
}
