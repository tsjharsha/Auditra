import { useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/State";
import { jsonPreview, shortId } from "../../lib/format";
import type { EvidenceItem } from "../../types/auditra";

export function EvidencePanel({
  evidence,
  selectedIds = [],
}: {
  evidence: EvidenceItem[];
  selectedIds?: string[];
}) {
  const [selected, setSelected] = useState<EvidenceItem | null>(evidence[0] ?? null);

  if (!evidence.length) {
    return <EmptyState title="No evidence attached" detail="Evidence is attached after a controller run." />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,420px)_1fr]">
      <Card>
        <SectionHeader title="Evidence" kicker={`${evidence.length} source-backed items`} />
        <div className="space-y-2">
          {evidence.map((item) => (
            <button
              key={item.evidence_id}
              className="w-full rounded-lg border border-line bg-white p-3 text-left hover:bg-slate-50"
              onClick={() => setSelected(item)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate font-mono text-xs font-bold text-ink">{item.evidence_id}</span>
                <Badge tone={selectedIds.includes(item.evidence_id) ? "success" : "muted"}>{item.entity_type}</Badge>
              </div>
              <div className="mt-2 text-sm text-muted">{item.summary}</div>
            </button>
          ))}
        </div>
      </Card>
      <Card>
        <SectionHeader
          title="Source Record"
          kicker={selected ? `${selected.entity_type}:${shortId(selected.entity_id, 24)}` : "No record"}
          action={selected ? <Button onClick={() => navigator.clipboard?.writeText(selected.evidence_id)}>Copy Evidence ID</Button> : null}
        />
        {selected ? (
          <pre className="max-h-[520px] overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
            {jsonPreview(selected.payload, 2600)}
          </pre>
        ) : (
          <EmptyState title="Select evidence" />
        )}
      </Card>
    </div>
  );
}
