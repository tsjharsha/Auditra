import { Activity, BarChart3, Boxes, ClipboardCheck, House, Settings, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { useAuditra } from "../hooks/useAuditra";
import { normalizePageId } from "../lib/navigation";
import { cn } from "../lib/utils";
import type { PrimaryPageId } from "../types/auditra";

const navigation: Array<{ id: PrimaryPageId; label: string; icon: ReactNode }> = [
  { id: "home", label: "Close", icon: <House className="h-4 w-4" /> },
  { id: "worlds", label: "Batch", icon: <Boxes className="h-4 w-4" /> },
  { id: "audits", label: "Audit", icon: <ShieldCheck className="h-4 w-4" /> },
  { id: "review", label: "Review", icon: <ClipboardCheck className="h-4 w-4" /> },
  { id: "insights", label: "Assurance", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "settings", label: "Settings", icon: <Settings className="h-4 w-4" /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { activePage, setActivePage, healthStatus, statusMessage, isBusy, busyLabel, world } = useAuditra();
  const currentPage = normalizePageId(activePage);
  const healthy = healthStatus === "healthy";

  return (
    <div className="min-h-screen bg-[#151515] text-[#f7f4ed]">
      <header className="sticky top-0 z-40 border-b border-white/[0.09] bg-[#151515]/95 backdrop-blur">
        <div className="mx-auto flex min-h-[60px] w-full max-w-[1440px] items-center gap-3 px-4 sm:px-6 lg:px-8">
          <button type="button" aria-label="Open Auditra close workspace" className="flex shrink-0 items-center gap-2.5 text-left" onClick={() => setActivePage("home")}>
            <span className="grid h-8 w-8 place-items-center rounded-md bg-[#c7ff54] text-[#1a2110]"><ShieldCheck className="h-4 w-4" /></span>
            <span className="hidden sm:block"><span className="block text-sm font-semibold text-white">AUDITRA</span><span className="block text-[10px] uppercase tracking-[0.08em] text-[#77746e]">Finance control</span></span>
          </button>
          <nav className="ml-1 flex min-w-0 flex-1 items-center gap-1 overflow-x-auto lg:ml-6" aria-label="Primary navigation">
            {navigation.map((item) => {
              const active = currentPage === item.id;
              return <button key={item.id} type="button" className={cn("inline-flex min-h-9 shrink-0 items-center gap-2 border-b-2 px-3 text-xs font-semibold transition sm:text-sm", active ? "border-[#c7ff54] text-[#d6ff82]" : "border-transparent text-[#9a9792] hover:text-white")} onClick={() => setActivePage(item.id)}>{item.icon}{item.label}</button>;
            })}
          </nav>
          <div className="hidden shrink-0 items-center gap-3 lg:flex">
            {world ? <span className="max-w-[170px] truncate text-xs text-[#77746e]">{world.summary.merchant}</span> : null}
            <span className={cn("inline-flex items-center gap-2 text-[11px] font-semibold", healthy ? "text-[#70f0bf]" : "text-[#ffb08d]")}><span className={cn("h-1.5 w-1.5 rounded-full", healthy ? "bg-[#70f0bf]" : "bg-[#ff6b4a]")} />{healthy ? "System ready" : "API offline"}</span>
          </div>
        </div>
        <div className="border-t border-white/[0.06] px-4 py-2 lg:hidden"><div className="mx-auto flex max-w-[1440px] items-center gap-2 text-xs text-[#9a9792]"><Activity className={cn("h-3.5 w-3.5 shrink-0", isBusy && "animate-pulse text-[#c7ff54]")} /><span className="truncate">{isBusy ? busyLabel + ": " + statusMessage : statusMessage}</span></div></div>
      </header>
      <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}