import {
  Activity,
  BarChart3,
  Boxes,
  ClipboardCheck,
  House,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { useAuditra } from "../hooks/useAuditra";
import { executionLabel } from "../lib/format";
import { normalizePageId } from "../lib/navigation";
import { cn } from "../lib/utils";
import type { PrimaryPageId } from "../types/auditra";

const navigation: Array<{ id: PrimaryPageId; label: string; icon: ReactNode }> = [
  { id: "home", label: "Home", icon: <House className="h-4 w-4" /> },
  { id: "worlds", label: "Worlds", icon: <Boxes className="h-4 w-4" /> },
  { id: "audits", label: "Audits", icon: <ShieldCheck className="h-4 w-4" /> },
  { id: "review", label: "Review", icon: <ClipboardCheck className="h-4 w-4" /> },
  { id: "insights", label: "Insights", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "settings", label: "Settings", icon: <Settings className="h-4 w-4" /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const {
    activePage,
    setActivePage,
    healthStatus,
    runtimeAI,
    statusMessage,
    isBusy,
    busyLabel,
    world,
    audit,
  } = useAuditra();
  const currentPage = normalizePageId(activePage);
  const provider = runtimeAI?.investigation;
  const healthy = healthStatus === "healthy";

  return (
    <div className="min-h-screen bg-[#070a10] text-slate-100">
      <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-[#090d14]/95 backdrop-blur-xl">
        <div className="mx-auto flex min-h-[68px] w-full max-w-[1600px] items-center gap-3 px-4 sm:px-6 lg:px-8">
          <button
            type="button"
            className="flex shrink-0 items-center gap-3 text-left"
            onClick={() => setActivePage("home")}
          >
            <span className="grid h-9 w-9 place-items-center rounded-md bg-cyan-400 text-slate-950 shadow-[0_0_28px_rgba(34,211,238,0.18)]">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <span className="hidden sm:block">
              <span className="block text-base font-semibold text-white">Auditra</span>
              <span className="block text-[10px] text-slate-500">Autonomous finance assurance</span>
            </span>
          </button>

          <nav
            className="ml-2 flex min-w-0 flex-1 items-center gap-1 overflow-x-auto lg:ml-8"
            aria-label="Primary navigation"
          >
            {navigation.map((item) => {
              const active = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={cn(
                    "inline-flex min-h-9 shrink-0 items-center gap-2 rounded-md px-3 text-xs font-semibold transition sm:text-sm",
                    active
                      ? "bg-white/[0.1] text-white"
                      : "text-slate-500 hover:bg-white/[0.05] hover:text-slate-200",
                  )}
                  onClick={() => setActivePage(item.id)}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="hidden shrink-0 items-center gap-2 xl:flex">
            {world ? (
              <span className="max-w-[150px] truncate border-r border-white/10 pr-3 text-xs text-slate-500">
                {world.summary.merchant}
              </span>
            ) : null}
            <ProviderBadge
              mode={provider?.execution_mode ?? "AI_UNAVAILABLE"}
              model={provider?.model ?? "Checking runtime"}
            />
            <span
              className={cn(
                "inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-[11px] font-semibold",
                healthy
                  ? "border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-200"
                  : "border-rose-400/20 bg-rose-400/[0.08] text-rose-200",
              )}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", healthy ? "bg-emerald-300" : "bg-rose-300")} />
              {healthy ? "API live" : healthStatus}
            </span>
          </div>
        </div>

        <div className="border-t border-white/[0.06] px-4 py-2 xl:hidden">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-3 text-xs">
            <span className="flex min-w-0 items-center gap-2 text-slate-500">
              <Activity className={cn("h-3.5 w-3.5 shrink-0", isBusy && "animate-pulse text-cyan-300")} />
              <span className="truncate">{isBusy ? busyLabel : statusMessage}</span>
            </span>
            <span className={healthy ? "shrink-0 text-emerald-300" : "shrink-0 text-rose-300"}>
              {healthy ? executionLabel(provider?.execution_mode) : "API offline"}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1600px] px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
        {children}
      </main>

      {audit ? <div className="sr-only">Current audit run {audit.controller_run.run_id}</div> : null}
    </div>
  );
}

function ProviderBadge({ mode, model }: { mode: string; model: string }) {
  const real = mode.startsWith("REAL_");
  const unavailable = mode === "AI_UNAVAILABLE";
  return (
    <span
      className={cn(
        "inline-flex max-w-[220px] items-center gap-2 rounded-md border px-2.5 py-1.5 text-[11px] font-semibold",
        real
          ? "border-cyan-400/20 bg-cyan-400/[0.08] text-cyan-200"
          : unavailable
            ? "border-rose-400/20 bg-rose-400/[0.08] text-rose-200"
            : "border-amber-400/20 bg-amber-400/[0.08] text-amber-200",
      )}
      title={mode + " / " + model}
    >
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", real ? "bg-cyan-300" : unavailable ? "bg-rose-300" : "bg-amber-300")} />
      <span className="truncate">{executionLabel(mode)}</span>
    </span>
  );
}
