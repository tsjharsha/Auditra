import { AlertOctagon } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import type { ReconciliationCase } from "../../types/auditra";

export function UnresolvedState({
  item,
  onReview,
}: {
  item: ReconciliationCase;
  onReview: () => void;
}) {
  if (!["HUMAN_REVIEW", "UNRESOLVED"].includes(item.status)) return null;

  const known = item.evidence.map((evidence) => evidence.evidence_id).slice(0, 6);
  const unknown = item.decision.verification?.challenges ?? [];
  const missing = item.decision.reason_codes.filter((code) => code.includes("MISSING") || code.includes("UNAVAILABLE"));

  return (
    <Card className="border-indigo-200 bg-indigo-50/70">
      <SectionHeader title="Insufficient Evidence" kicker="Automation stopped because the decision requires review confidence." />
      <div className="grid gap-3 md:grid-cols-3">
        <List title="Known" rows={known} fallback="Visible source evidence is attached." />
        <List title="Unknown" rows={unknown} fallback="No unresolved challenge details were reported." />
        <List title="Missing Evidence" rows={missing} fallback="No explicit missing-evidence code." />
      </div>
      <div className="mt-4 flex items-center justify-between gap-3 rounded-lg border border-indigo-200 bg-white p-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-indigo">
          <AlertOctagon className="h-4 w-4" />
          Why automation stopped: {item.decision.reason_codes.join(", ") || "manual review required"}
        </div>
        <Button variant="primary" onClick={onReview}>Send To Human Review</Button>
      </div>
    </Card>
  );
}

function List({ title, rows, fallback }: { title: string; rows: string[]; fallback: string }) {
  return (
    <div className="rounded-lg border border-indigo-200 bg-white p-3">
      <div className="text-xs font-bold uppercase text-muted">{title}</div>
      <div className="mt-2 space-y-1 text-sm text-ink">
        {(rows.length ? rows : [fallback]).map((row) => (
          <div key={row}>{row}</div>
        ))}
      </div>
    </div>
  );
}
