import { cn } from "../../lib/utils";

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: T; label: string; count?: number }>;
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-lg border border-line bg-slate-100 p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={cn(
            "min-h-9 min-w-max rounded-md px-3 text-sm font-semibold text-muted transition",
            active === tab.id ? "bg-white text-ink shadow-sm" : "hover:bg-white/70",
          )}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {tab.count !== undefined ? <span className="ml-2 text-xs text-muted">{tab.count}</span> : null}
        </button>
      ))}
    </div>
  );
}
