import {
  Activity,
  BarChart3,
  BookOpenCheck,
  Boxes,
  ClipboardCheck,
  GitBranch,
  Home,
  ListChecks,
  Network,
  PlayCircle,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import type { ReactNode } from "react";
import { API_BASE } from "../api/client";
import { cn } from "../lib/utils";
import { useAuditra } from "../hooks/useAuditra";
import type { PageId } from "../types/auditra";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";

const navItems: Array<{ id: PageId; label: string; icon: ReactNode }> = [
  { id: "home", label: "Home", icon: <Home className="h-4 w-4" /> },
  { id: "world-builder", label: "World Builder", icon: <Workflow className="h-4 w-4" /> },
  { id: "world-explorer", label: "World Explorer", icon: <Boxes className="h-4 w-4" /> },
  { id: "reconciliation", label: "Reconciliation", icon: <ListChecks className="h-4 w-4" /> },
  { id: "investigations", label: "Investigations", icon: <ShieldCheck className="h-4 w-4" /> },
  { id: "evidence-graph", label: "Evidence Graph", icon: <GitBranch className="h-4 w-4" /> },
  { id: "human-review", label: "Human Review", icon: <ClipboardCheck className="h-4 w-4" /> },
  { id: "evaluation-lab", label: "Evaluation Lab", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "controller-runs", label: "Controller Runs", icon: <Activity className="h-4 w-4" /> },
  { id: "audit-trail", label: "Audit Trail", icon: <BookOpenCheck className="h-4 w-4" /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { activePage, setActivePage, healthStatus, statusMessage, isBusy, busyLabel, runFiveMinuteDemo, world, audit } = useAuditra();
  const healthTone = healthStatus === "healthy" ? "success" : healthStatus === "offline" ? "danger" : "warning";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-line bg-white/95 backdrop-blur">
        <div className="flex flex-col gap-3 px-4 py-3 xl:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button className="flex min-w-0 items-center gap-3 text-left" onClick={() => setActivePage("home")}>
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-ink text-white">
                <Network className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="text-lg font-black uppercase leading-none tracking-normal text-ink">Auditra</div>
                <div className="mt-1 truncate text-xs font-medium text-muted">From financial intent to verified control.</div>
              </div>
            </button>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={healthTone}>{healthStatus}</Badge>
              <Badge tone={isBusy ? "review" : "muted"}>{isBusy ? busyLabel : statusMessage}</Badge>
              {world ? <Badge tone="info">{world.world_id}</Badge> : null}
              {audit ? <Badge tone={audit.evaluation.failures.length ? "warning" : "success"}>{audit.survival_status}</Badge> : null}
              <Button variant="primary" icon={<PlayCircle className="h-4 w-4" />} onClick={() => void runFiveMinuteDemo()} disabled={isBusy}>
                Run 5-Minute Demo
              </Button>
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto pb-1">
            {navItems.map((item) => (
              <button
                key={item.id}
                className={cn(
                  "inline-flex min-h-9 min-w-max items-center gap-2 rounded-lg px-3 text-sm font-semibold transition",
                  activePage === item.id ? "bg-ink text-white" : "text-steel hover:bg-slate-100",
                )}
                onClick={() => setActivePage(item.id)}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1520px] px-4 py-5 xl:px-6">
        <div className="mb-3 text-xs font-medium text-muted">API: {API_BASE}</div>
        {children}
      </main>
    </div>
  );
}
