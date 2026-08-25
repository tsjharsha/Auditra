import {
  Bell,
  ChevronRight,
  CircleHelp,
  Home,
  Layers3,
  Network,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  UserCircle2,
  WandSparkles,
  PlayCircle,
  WalletCards,
} from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { API_BASE } from "../api/client";
import { normalizePageId } from "../lib/navigation";
import { cn } from "../lib/utils";
import { useAuditra } from "../hooks/useAuditra";
import type { PageId, PrimaryPageId } from "../types/auditra";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { Input } from "./ui/Field";

const navItems: Array<{ id: PrimaryPageId; label: string; icon: ReactNode }> = [
  { id: "home", label: "Home", icon: <Home className="h-4 w-4" /> },
  { id: "worlds", label: "Worlds", icon: <WandSparkles className="h-4 w-4" /> },
  { id: "audits", label: "Audits", icon: <WalletCards className="h-4 w-4" /> },
  { id: "review", label: "Review", icon: <ShieldCheck className="h-4 w-4" /> },
  { id: "insights", label: "Insights", icon: <Sparkles className="h-4 w-4" /> },
  { id: "settings", label: "Settings", icon: <Settings2 className="h-4 w-4" /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { activePage, setActivePage, healthStatus, statusMessage, isBusy, busyLabel, runFiveMinuteDemo, world, audit, selectCase } = useAuditra();
  const [query, setQuery] = useState("");
  const currentPage = normalizePageId(activePage);
  const healthTone = healthStatus === "healthy" ? "success" : healthStatus === "offline" ? "danger" : "warning";
  const attentionCount = useMemo(
    () => audit?.controller_run.cases.filter((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status)).length ?? 0,
    [audit],
  );
  const pageMeta = {
    home: {
      title: "Home",
      eyebrow: "Workspace",
      detail: "See what matters, what changed, and what to do next.",
    },
    worlds: {
      title: "Worlds",
      eyebrow: "Create",
      detail: "Describe, review, build, audit, and explore financial worlds.",
    },
    audits: {
      title: "Audits",
      eyebrow: "Audit",
      detail: "Track audit health, exposure, and the cases that need attention.",
    },
    review: {
      title: "Review",
      eyebrow: "Review",
      detail: "Investigate important exceptions and make clear decisions.",
    },
    insights: {
      title: "Insights",
      eyebrow: "Trust",
      detail: "Understand accuracy, exposure, AI value, and advanced testing.",
    },
    settings: {
      title: "Settings",
      eyebrow: "Workspace",
      detail: "Manage workspace, AI, data, and security preferences.",
    },
  }[currentPage];

  function handleSearch() {
    const value = query.trim().toLowerCase();
    if (!value) return;
    const matchedCase = audit?.controller_run.cases.find(
      (item) =>
        item.case_id.toLowerCase().includes(value) ||
        item.payment_id.toLowerCase().includes(value) ||
        (item.order_id ?? "").toLowerCase().includes(value),
    );
    if (matchedCase) {
      selectCase(matchedCase.case_id);
      setQuery("");
      return;
    }
    if (value.includes("world")) {
      setActivePage("worlds");
    } else if (value.includes("review") || value.includes("exception")) {
      setActivePage("review");
    } else if (value.includes("insight") || value.includes("performance") || value.includes("baseline")) {
      setActivePage("insights");
    } else if (value.includes("setting") || value.includes("security")) {
      setActivePage("settings");
    } else {
      setActivePage("audits");
    }
    setQuery("");
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.10),transparent_28%),radial-gradient(circle_at_top_right,rgba(14,165,233,0.10),transparent_24%),linear-gradient(180deg,#fffdf9_0%,#f7f8fc_52%,#f3f5fb_100%)]">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] gap-6 px-4 py-4 xl:px-6">
        <aside className="hidden w-[248px] shrink-0 rounded-[28px] border border-white/70 bg-slate-950/95 p-5 text-white shadow-[0_24px_80px_rgba(15,23,42,0.28)] xl:flex xl:flex-col">
          <button className="flex items-center gap-3 text-left" onClick={() => setActivePage("home")}>
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-indigo-500 via-sky-500 to-cyan-400 text-white shadow-lg">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight">Auditra</div>
              <div className="text-xs text-slate-400">Know what matters before money becomes a problem.</div>
            </div>
          </button>

          <nav className="mt-8 space-y-1.5">
            {navItems.map((item) => {
              const active = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  className={cn(
                    "flex min-h-11 w-full items-center gap-3 rounded-2xl px-3.5 text-left text-sm font-medium transition",
                    active ? "bg-white text-slate-950 shadow-sm" : "text-slate-300 hover:bg-white/10 hover:text-white",
                  )}
                  onClick={() => setActivePage(item.id)}
                >
                  <span className={cn("grid h-8 w-8 place-items-center rounded-xl", active ? "bg-slate-100 text-indigo-600" : "bg-white/10 text-slate-300")}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="mt-8 rounded-3xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-400">Workspace</div>
                <div className="mt-1 text-sm font-semibold text-white">{world?.summary.merchant ?? "No world yet"}</div>
              </div>
              <Badge tone={healthTone}>{healthStatus}</Badge>
            </div>
            <div className="mt-3 text-sm leading-6 text-slate-300">{isBusy ? busyLabel : statusMessage}</div>
            {audit ? <div className="mt-3 text-xs text-slate-400">{attentionCount} cases need attention</div> : null}
          </div>

          <div className="mt-auto space-y-2 pt-8">
            <button className="flex min-h-11 w-full items-center gap-3 rounded-2xl px-3.5 text-left text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white" onClick={() => setActivePage("settings")}>
              <span className="grid h-8 w-8 place-items-center rounded-xl bg-white/10">
                <CircleHelp className="h-4 w-4" />
              </span>
              Help
            </button>
            <button className="flex min-h-11 w-full items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-3.5 text-left text-sm font-medium text-white transition hover:bg-white/10" onClick={() => setActivePage("settings")}>
              <span className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-500">
                <UserCircle2 className="h-4 w-4" />
              </span>
              <span>
                <span className="block">Workspace owner</span>
                <span className="block text-xs text-slate-400">Open profile and preferences</span>
              </span>
            </button>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-4 z-30 rounded-[28px] border border-white/70 bg-white/85 px-4 py-4 shadow-[0_16px_48px_rgba(15,23,42,0.08)] backdrop-blur xl:px-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <span>{pageMeta.eyebrow}</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                  <span>{pageMeta.title}</span>
                </div>
                <div className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{pageMeta.title}</div>
                <div className="mt-1 text-sm text-muted">{pageMeta.detail}</div>
              </div>

              <div className="flex flex-col gap-3 lg:items-end">
                <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
                  <form
                    className="relative min-w-[260px] flex-1 lg:w-[340px] lg:flex-none"
                    onSubmit={(event) => {
                      event.preventDefault();
                      handleSearch();
                    }}
                  >
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input className="rounded-2xl border-white bg-slate-50 pl-9 shadow-none" placeholder="Search worlds, cases, or reviews" value={query} onChange={(event) => setQuery(event.target.value)} />
                  </form>
                  <button className="grid h-10 w-10 place-items-center rounded-2xl border border-line bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-950" onClick={() => setActivePage(attentionCount ? "review" : "audits")}>
                    <Bell className="h-4 w-4" />
                  </button>
                  <Button variant="primary" icon={<PlayCircle className="h-4 w-4" />} onClick={() => void runFiveMinuteDemo()} disabled={isBusy}>
                    Run Demo
                  </Button>
                  <button className="grid h-10 w-10 place-items-center rounded-2xl border border-line bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-950" onClick={() => setActivePage("settings")}>
                    <UserCircle2 className="h-5 w-5" />
                  </button>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={healthTone}>{healthStatus}</Badge>
                  <Badge tone={isBusy ? "review" : "muted"}>{isBusy ? busyLabel : statusMessage}</Badge>
                  {world ? <Badge tone="info">{world.summary.merchant}</Badge> : null}
                  {audit ? <Badge tone={attentionCount ? "warning" : "success"}>{audit.survival_status}</Badge> : null}
                </div>
              </div>
            </div>
          </header>

          <main className="pb-8 pt-6">
            <div className="mb-4 flex flex-wrap items-center gap-2 text-xs font-medium text-muted">
              <span className="rounded-full border border-white/70 bg-white/70 px-3 py-1">API: {API_BASE}</span>
              {world ? <span className="rounded-full border border-white/70 bg-white/70 px-3 py-1">World: {world.world_id}</span> : null}
              {audit ? <span className="rounded-full border border-white/70 bg-white/70 px-3 py-1">Run: {audit.controller_run.run_id}</span> : null}
            </div>
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
