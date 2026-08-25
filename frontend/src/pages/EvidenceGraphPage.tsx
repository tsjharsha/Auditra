import { GitBranch } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/State";
import { CaseEvidenceFlow } from "../features/graph/RelationshipFlow";
import { shortId } from "../lib/format";
import { statusTone } from "../lib/status";
import { useAuditra } from "../hooks/useAuditra";
import type { ReconciliationCase } from "../types/auditra";

export function EvidenceGraphPage() {
  const { audit, selectedCase, setSelectedCase, setActivePage } = useAuditra();
  const cases = audit?.controller_run.cases ?? [];

  if (!audit) {
    return <EmptyState title="No evidence graph" detail="Audit a world to create transaction-level evidence graphs." />;
  }

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader
          title="Evidence Graph"
          kicker={selectedCase ? `${selectedCase.payment_id} / ${selectedCase.graph.nodes.length} nodes` : "Select a reconciliation case"}
          action={<Button icon={<GitBranch className="h-4 w-4" />} disabled={!selectedCase} onClick={() => setActivePage("investigations")}>Open Investigation</Button>}
        />
        <DataTable rows={cases} columns={columns} getRowId={(row) => row.case_id} onRowClick={setSelectedCase} initialPageSize={10} />
      </Card>
      <CaseEvidenceFlow graph={selectedCase?.graph} />
    </div>
  );
}

const columns: Column<ReconciliationCase>[] = [
  {
    key: "payment",
    header: "Payment",
    value: (row) => row.payment_id,
    sortValue: (row) => row.payment_id,
    className: "font-mono text-xs",
  },
  {
    key: "case",
    header: "Case",
    value: (row) => shortId(row.case_id, 22),
    sortValue: (row) => row.case_id,
    className: "font-mono text-xs",
  },
  {
    key: "status",
    header: "Status",
    value: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
    sortValue: (row) => row.status,
  },
  {
    key: "nodes",
    header: "Nodes",
    value: (row) => row.graph.nodes.length,
    sortValue: (row) => row.graph.nodes.length,
  },
  {
    key: "edges",
    header: "Edges",
    value: (row) => row.graph.edges.length,
    sortValue: (row) => row.graph.edges.length,
  },
];
