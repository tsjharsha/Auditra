import { useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Card, SectionHeader } from "../../components/ui/Card";
import { Tabs } from "../../components/ui/Tabs";
import type { SchemaPreview } from "../../types/auditra";
import { EmptyState } from "../../components/ui/State";

export function SchemaBrowser({ schema }: { schema?: SchemaPreview | null }) {
  const [active, setActive] = useState<string | null>(schema?.entities[0]?.entity ?? null);
  const entities = schema?.entities ?? [];
  const selected = entities.find((entity) => entity.entity === active) ?? entities[0];

  if (!schema) return <EmptyState title="No schema yet" detail="Preview or generate a world to inspect entities and fields." />;

  return (
    <Card>
      <SectionHeader title="Schema" kicker="Canonical records produced by the world builder" />
      <Tabs
        tabs={entities.map((entity) => ({ id: entity.entity, label: entity.entity.replace("_", " "), count: entity.fields.length }))}
        active={selected?.entity ?? entities[0].entity}
        onChange={setActive}
      />
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {(selected?.fields ?? []).map((field) => (
          <div key={field.name} className="rounded-lg border border-line bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="font-mono text-sm font-bold text-ink">{field.name}</div>
              <Badge tone={field.required ? "success" : "muted"}>{field.required ? "required" : "optional"}</Badge>
            </div>
            <div className="mt-2 text-sm text-muted">{field.type}</div>
            {field.description ? <div className="mt-2 text-xs leading-5 text-muted">{field.description}</div> : null}
          </div>
        ))}
      </div>
    </Card>
  );
}
