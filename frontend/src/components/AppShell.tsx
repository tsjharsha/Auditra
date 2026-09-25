import { Zap } from "lucide-react";
import type { ReactNode } from "react";
import { useAuditra } from "../hooks/useAuditra";
import { cn } from "../lib/utils";

const navigation = [
  { id: "warroom", label: "Zero-Trust Verification", icon: <Zap className="h-4 w-4" /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { isBusy, busyLabel, statusMessage } = useAuditra();
  
  return (
    <div className="min-h-screen bg-[#0c0c14] text-[#f7f4ed]">
      <header className="sticky top-0 z-40 border-b border-white/[0.09] bg-[#0c0c14]/95 backdrop-blur">
        <div className="mx-auto flex min-h-[60px] w-full max-w-[1440px] items-center gap-3 px-4 sm:px-6 lg:px-8">
          <div className="flex shrink-0 items-center gap-2.5 text-left">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-[#c7ff54] text-[#1a2110]"><Zap className="h-4 w-4" /></span>
            <span className="hidden sm:block"><span className="block text-sm font-semibold text-white">AUDITRA</span><span className="block text-[10px] uppercase tracking-[0.08em] text-[#77746e]">Zero-Trust Fabric</span></span>
          </div>
          <nav className="ml-1 flex min-w-0 flex-1 items-center gap-1 overflow-x-auto lg:ml-6" aria-label="Primary navigation">
            {navigation.map((item) => {
              return <div key={item.id} className={cn("inline-flex min-h-9 shrink-0 items-center gap-2 border-b-2 px-3 text-xs font-semibold transition sm:text-sm border-[#c7ff54] text-[#d6ff82]")}>{item.icon}{item.label}</div>;
            })}
          </nav>
          <div className="hidden shrink-0 items-center gap-3 lg:flex">
            <span className={cn("inline-flex items-center gap-2 text-[11px] font-semibold text-[#70f0bf]")}><span className={cn("h-1.5 w-1.5 rounded-full bg-[#70f0bf]")} />Matrix Online</span>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}