import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

type Tone = "success" | "danger" | "warning" | "review" | "muted" | "info";

const tones: Record<Tone, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  review: "border-indigo-200 bg-indigo-50 text-indigo-700",
  muted: "border-line bg-slate-50 text-muted",
  info: "border-sky-200 bg-sky-50 text-sky-700",
};

export function Badge({ tone = "muted", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex min-h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-bold uppercase tracking-normal",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
