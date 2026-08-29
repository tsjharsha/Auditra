import { Activity, Database, Hammer, Network, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { useAuditra } from "../hooks/useAuditra";
import { normalizePageId } from "../lib/navigation";
import { cn } from "../lib/utils";
import type { PrimaryPageId } from "../types/auditra";

const navigation: Array<{ id: PrimaryPageId; label: string; icon: ReactNode }> = [
  { id: "home", label: "Build", icon: <Hammer className="h-4 w-4" /> },
  { id: "audits", label: "Audit", icon: <ShieldCheck className="h-4 w-4" /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { activePage, setActivePage, healthStatus, statusMessage, isBusy, busyLabel, world, audit } = useAuditra();
  const currentPage = normalizePageId(activePage);
  const healthy = healthStatus === "healthy";

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050914] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(125deg,rgba(79,70,229,0.16)_0%,transparent_32%,rgba(8,145,178,0.12)_67%,transparent_100%)]" />
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:56px_56px] [mask-image:linear-gradient(to_bottom,black,transparent_78%)]" />

      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#050914]/85 backdrop-blur-xl">
        <div className="mx-auto flex min-h-[72px] w-full max-w-[1480px] items-center gap-4 px-4 sm:px-6 lg:px-8">
          <button type="button" className="flex shrink-0 items-center gap-3 text-left" onClick={() => setActivePage("home")}>
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 via-sky-500 to-cyan-400 text-white shadow-[0_0_24px_rgba(34,211,238,0.28)]">
              <Network className="h-5 w-5" />
            </span>
            <span className="hidden sm:block">
              <span className="block text-lg font-bold text-white">Auditra</span>
              <span className="block text-[11px] text-slate-500">Financial control intelligence</span>
            </span>
          </button>

          <nav className="ml-auto flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.035] p-1 sm:ml-6" aria-label="Primary navigation">
            {navigation.map((item) => {
              const active = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={cn(
                    "inline-flex min-h-10 items-center gap-2 rounded-md px-3 text-sm font-semibold transition sm:px-4",
                    active ? "bg-white text-slate-950 shadow-sm" : "text-slate-400 hover:bg-white/5 hover:text-white",
                  )}
                  onClick={() => setActivePage(item.id)}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="ml-auto hidden min-w-0 items-center gap-3 lg:flex">
            {world ? (
              <div className="flex min-w-0 items-center gap-2 border-r border-white/10 pr-3 text-xs text-slate-400">
                <Database className="h-4 w-4 shrink-0 text-indigo-300" />
                <span className="max-w-[180px] truncate">{world.summary.merchant}</span>
              </div>
            ) : null}
            <div className="flex min-w-0 items-center gap-2 text-xs text-slate-400">
              <Activity className={cn("h-4 w-4 shrink-0", isBusy ? "animate-pulse text-cyan-300" : "text-slate-500")} />
              <span className="max-w-[180px] truncate">{isBusy ? busyLabel : statusMessage}</span>
            </div>
            <div className={cn("inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold", healthy ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200" : "border-amber-400/20 bg-amber-400/10 text-amber-200")}>
              <span className="relative flex h-2 w-2">
                {healthy ? <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-60" /> : null}
                <span className={cn("relative inline-flex h-2 w-2 rounded-full", healthy ? "bg-emerald-300" : "bg-amber-300")} />
              </span>
              {healthy ? "API live" : healthStatus}
            </div>
          </div>
        </div>

        <div className="border-t border-white/[0.06] px-4 py-2 lg:hidden">
          <div className="mx-auto flex max-w-[1480px] items-center justify-between gap-3 text-xs text-slate-500">
            <span className="truncate">{isBusy ? busyLabel : statusMessage}</span>
            <span className={cn("shrink-0", healthy ? "text-emerald-300" : "text-amber-300")}>{healthy ? "API live" : healthStatus}</span>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-[1480px] px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
        {children}
      </main>

      {audit ? <div className="sr-only">Current audit run {audit.controller_run.run_id}</div> : null}
    </div>
  );
}
