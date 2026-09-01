import { AlertTriangle, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export type Accent = "cyan" | "indigo" | "emerald" | "amber" | "rose" | "slate";

const accentStyles: Record<Accent, { icon: string; value: string; bar: string; pill: string }> = {
  cyan: { icon: "border-[#c7ff54]/25 bg-[#c7ff54]/10 text-[#d6ff82]", value: "text-[#d6ff82]", bar: "from-[#c7ff54] to-[#70f0bf]", pill: "border-[#c7ff54]/25 bg-[#c7ff54]/10 text-[#d6ff82]" },
  indigo: { icon: "border-[#f7c74d]/25 bg-[#f7c74d]/10 text-[#f7d778]", value: "text-[#f7d778]", bar: "from-[#f7c74d] to-[#ff9b70]", pill: "border-[#f7c74d]/25 bg-[#f7c74d]/10 text-[#f7d778]" },
  emerald: { icon: "border-[#70f0bf]/25 bg-[#70f0bf]/10 text-[#70f0bf]", value: "text-[#70f0bf]", bar: "from-[#70f0bf] to-[#c7ff54]", pill: "border-[#70f0bf]/25 bg-[#70f0bf]/10 text-[#70f0bf]" },
  amber: { icon: "border-[#f7c74d]/25 bg-[#f7c74d]/10 text-[#f7d778]", value: "text-[#f7d778]", bar: "from-[#f7c74d] to-[#ff9b70]", pill: "border-[#f7c74d]/25 bg-[#f7c74d]/10 text-[#f7d778]" },
  rose: { icon: "border-[#ff6b4a]/25 bg-[#ff6b4a]/10 text-[#ffb08d]", value: "text-[#ffb08d]", bar: "from-[#ff6b4a] to-[#f7c74d]", pill: "border-[#ff6b4a]/25 bg-[#ff6b4a]/10 text-[#ffb08d]" },
  slate: { icon: "border-white/10 bg-white/5 text-[#c7c4bf]", value: "text-white", bar: "from-[#c7c4bf] to-[#77736e]", pill: "border-white/10 bg-white/5 text-[#c7c4bf]" },
};

export function WorkspacePanel({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("rounded-lg border border-white/10 bg-[#201f21] p-5 shadow-[0_18px_55px_rgba(0,0,0,0.18)] sm:p-6", className)}>{children}</section>;
}

export function SectionTitle({ icon, eyebrow, title, detail, action }: { icon?: ReactNode; eyebrow?: string; title: string; detail?: string; action?: ReactNode }) {
  return <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div className="flex min-w-0 gap-3">{icon ? <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[#c7ff54]/20 bg-[#c7ff54]/10 text-[#d6ff82]">{icon}</span> : null}<div className="min-w-0">{eyebrow ? <div className="text-xs font-semibold uppercase tracking-[0.08em] text-[#c7ff54]">{eyebrow}</div> : null}<h2 className="mt-1 text-lg font-semibold text-white sm:text-xl">{title}</h2>{detail ? <p className="mt-1 max-w-3xl text-sm leading-6 text-[#9a9792]">{detail}</p> : null}</div></div>{action ? <div className="shrink-0">{action}</div> : null}</div>;
}

export function MetricTile({ label, value, detail, icon, accent = "slate" }: { label: string; value: ReactNode; detail?: ReactNode; icon?: ReactNode; accent?: Accent }) {
  const style = accentStyles[accent];
  return <div className="min-h-[130px] rounded-lg border border-white/[0.1] bg-[#201f21] p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20"><div className="flex items-start justify-between gap-3"><div className="text-sm font-medium text-[#9a9792]">{label}</div>{icon ? <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-md border", style.icon)}>{icon}</span> : null}</div><div className={cn("mt-4 break-words text-2xl font-semibold", style.value)}>{value}</div>{detail ? <div className="mt-2 text-xs leading-5 text-[#77736e]">{detail}</div> : null}</div>;
}

export function StatusPill({ children, accent = "slate", dot = false }: { children: ReactNode; accent?: Accent; dot?: boolean }) {
  return <span className={cn("inline-flex min-h-7 items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold", accentStyles[accent].pill)}>{dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}{children}</span>;
}

export function SegmentedTabs<T extends string>({ tabs, active, onChange }: { tabs: Array<{ id: T; label: string; count?: number; icon?: ReactNode }>; active: T; onChange: (id: T) => void }) {
  return <div className="flex max-w-full gap-1 overflow-x-auto rounded-lg border border-white/10 bg-black/20 p-1" role="tablist">{tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={active === tab.id} className={cn("inline-flex min-h-10 min-w-max items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition", active === tab.id ? "bg-[#c7ff54] text-[#1b2114] shadow-sm" : "text-[#9a9792] hover:bg-white/5 hover:text-white")} onClick={() => onChange(tab.id)}>{tab.icon}{tab.label}{tab.count !== undefined ? <span className={cn("rounded-full px-1.5 py-0.5 text-[11px]", active === tab.id ? "bg-[#b1e743] text-[#1b2114]" : "bg-white/10 text-[#c7c4bf]")}>{tab.count}</span> : null}</button>)}</div>;
}

export function InlineError({ error, title = "Auditra could not complete this step" }: { error: unknown; title?: string }) {
  const detail = error instanceof Error ? error.message : String(error ?? "Unknown error");
  return <div className="rounded-lg border border-[#ff6b4a]/30 bg-[#ff6b4a]/10 p-4 text-[#ffd3c7]"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[#ffb08d]" /><div className="min-w-0"><div className="text-sm font-semibold">{title}</div><details className="mt-2 text-sm text-[#ffb08d]"><summary className="cursor-pointer">Technical details</summary><p className="mt-2 break-words leading-6">{detail}</p></details></div></div></div>;
}

export function BusyOverlay({ label }: { label: string }) {
  return <div className="absolute inset-0 z-20 grid place-items-center rounded-lg bg-[#171618]/85 p-6 text-center backdrop-blur-sm"><div><LoaderCircle className="mx-auto h-8 w-8 animate-spin text-[#c7ff54]" /><div className="mt-3 text-sm font-semibold text-white">{label}</div><div className="mt-1 text-xs text-[#9a9792]">This usually takes a few seconds.</div></div></div>;
}

export function ProgressBar({ value, accent = "cyan" }: { value: number; accent?: Accent }) {
  const width = String(Math.max(3, Math.min(100, value * 100))) + "%";
  return <div className="h-2 overflow-hidden rounded-full bg-white/10"><div className={cn("h-full rounded-full bg-gradient-to-r transition-[width] duration-700", accentStyles[accent].bar)} style={{ width }} /></div>;
}
