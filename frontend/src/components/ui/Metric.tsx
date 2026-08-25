import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

export function Metric({
  label,
  value,
  detail,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "default" | "success" | "danger" | "warning" | "review";
}) {
  const toneClass = {
    default: "border-line",
    success: "border-emerald-200 bg-emerald-50/60",
    danger: "border-rose-200 bg-rose-50/70",
    warning: "border-amber-200 bg-amber-50/70",
    review: "border-indigo-200 bg-indigo-50/70",
  }[tone];
  return (
    <div className={cn("min-h-24 rounded-lg border bg-white p-3", toneClass)}>
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="mt-2 break-words text-2xl font-bold leading-tight text-ink">{value}</div>
      {detail ? <div className="mt-1 text-xs text-muted">{detail}</div> : null}
    </div>
  );
}

export function MetricGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">{children}</div>;
}
