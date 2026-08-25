import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("rounded-lg border border-line bg-white p-4 shadow-panel", className)}>{children}</section>;
}

export function SectionHeader({
  title,
  kicker,
  action,
}: {
  title: string;
  kicker?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-base font-bold text-ink">{title}</h2>
        {kicker ? <p className="mt-1 text-sm text-muted">{kicker}</p> : null}
      </div>
      {action}
    </div>
  );
}
