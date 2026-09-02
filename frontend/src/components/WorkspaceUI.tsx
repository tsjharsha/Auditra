import { AlertTriangle, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export type Accent = "cyan" | "indigo" | "emerald" | "amber" | "rose" | "slate";

const accentStyles: Record<Accent, { icon: string; value: string; bar: string; pill: string }> = {
  cyan: { icon: "text-[#d6ff82]", value: "text-[#d6ff82]", bar: "bg-[#c7ff54]", pill: "border-[#c7ff54]/25 text-[#d6ff82]" },
  indigo: { icon: "text-[#f7d778]", value: "text-[#f7d778]", bar: "bg-[#f7c74d]", pill: "border-[#f7c74d]/25 text-[#f7d778]" },
  emerald: { icon: "text-[#70f0bf]", value: "text-[#70f0bf]", bar: "bg-[#70f0bf]", pill: "border-[#70f0bf]/25 text-[#70f0bf]" },
  amber: { icon: "text-[#f7d778]", value: "text-[#f7d778]", bar: "bg-[#f7c74d]", pill: "border-[#f7c74d]/25 text-[#f7d778]" },
  rose: { icon: "text-[#ffb08d]", value: "text-[#ffb08d]", bar: "bg-[#ff6b4a]", pill: "border-[#ff6b4a]/25 text-[#ffb08d]" },
  slate: { icon: "text-[#c7c4bf]", value: "text-white", bar: "bg-[#77736e]", pill: "border-white/10 text-[#c7c4bf]" },
};

export function WorkspacePanel({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("border-y border-white/10 py-5 sm:py-6", className)}>{children}</section>;
}

export function SectionTitle({ icon, eyebrow, title, detail, action }: { icon?: ReactNode; eyebrow?: string; title: string; detail?: string; action?: ReactNode }) {
  return <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0">{eyebrow ? <div className="section-kicker">{eyebrow}</div> : null}<div className="flex items-center gap-2"><h2 className="mt-1 text-lg font-semibold text-white sm:text-xl">{title}</h2>{icon ? <span className="text-[#aaa7a1]">{icon}</span> : null}</div>{detail ? <p className="mt-1 max-w-3xl text-sm leading-6 text-[#aaa7a1]">{detail}</p> : null}</div>{action ? <div className="shrink-0">{action}</div> : null}</div>;
}

export function MetricTile({ label, value, detail, icon, accent = "slate" }: { label: string; value: ReactNode; detail?: ReactNode; icon?: ReactNode; accent?: Accent }) {
  const style = accentStyles[accent];
  return <div className="min-h-[96px] border-l border-white/10 px-4 py-1"><div className="flex items-center justify-between gap-3"><div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-[#77736e]">{label}</div>{icon ? <span className={style.icon}>{icon}</span> : null}</div><div className={cn("mt-3 break-words text-2xl font-semibold", style.value)}>{value}</div>{detail ? <div className="mt-1 text-xs leading-5 text-[#77736e]">{detail}</div> : null}</div>;
}

export function StatusPill({ children, accent = "slate", dot = false }: { children: ReactNode; accent?: Accent; dot?: boolean }) {
  return <span className={cn("inline-flex min-h-6 items-center gap-2 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold", accentStyles[accent].pill)}>{dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}{children}</span>;
}

export function SegmentedTabs<T extends string>({ tabs, active, onChange }: { tabs: Array<{ id: T; label: string; count?: number; icon?: ReactNode }>; active: T; onChange: (id: T) => void }) {
  return <div className="flex max-w-full gap-1 overflow-x-auto border-b border-white/10" role="tablist">{tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={active === tab.id} className={cn("inline-flex min-h-10 min-w-max items-center justify-center gap-2 border-b-2 px-3 text-sm font-medium transition", active === tab.id ? "border-[#c7ff54] text-[#d6ff82]" : "border-transparent text-[#77736e] hover:text-white")} onClick={() => onChange(tab.id)}>{tab.icon}{tab.label}{tab.count !== undefined ? <span className="text-[11px] text-[#aaa7a1]">{tab.count}</span> : null}</button>)}</div>;
}

export function InlineError({ error, title = "Auditra could not complete this step" }: { error: unknown; title?: string }) {
  const detail = error instanceof Error ? error.message : String(error ?? "Unknown error");
  return <div className="border-y border-[#ff6b4a]/35 bg-[#ff6b4a]/[0.07] py-4 text-[#ffd3c7]"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[#ffb08d]" /><div className="min-w-0"><div className="text-sm font-semibold">{title}</div><details className="mt-2 text-sm text-[#ffb08d]"><summary className="cursor-pointer">Technical details</summary><p className="mt-2 break-words leading-6">{detail}</p></details></div></div></div>;
}

export function BusyOverlay({ label }: { label: string }) {
  return <div className="absolute inset-0 z-20 grid place-items-center bg-[#151515]/90 p-6 text-center"><div><LoaderCircle className="mx-auto h-8 w-8 animate-spin text-[#c7ff54]" /><div className="mt-3 text-sm font-semibold text-white">{label}</div></div></div>;
}

export function ProgressBar({ value, accent = "cyan" }: { value: number; accent?: Accent }) {
  const width = String(Math.max(3, Math.min(100, value * 100))) + "%";
  return <div className="h-1.5 overflow-hidden bg-white/10"><div className={cn("h-full transition-[width] duration-500", accentStyles[accent].bar)} style={{ width }} /></div>;
}