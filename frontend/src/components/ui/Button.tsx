import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";

const variants: Record<Variant, string> = {
  primary: "border-ink bg-ink text-white hover:bg-steel",
  secondary: "border-line bg-white text-ink hover:bg-slate-50",
  ghost: "border-transparent bg-transparent text-steel hover:bg-white",
  danger: "border-rose/30 bg-rose/10 text-rose hover:bg-rose/15",
  success: "border-teal bg-teal text-white hover:bg-teal/90",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: ReactNode;
}

export function Button({ variant = "secondary", icon, className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
