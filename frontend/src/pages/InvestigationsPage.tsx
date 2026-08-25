import { Badge } from "../components/ui/Badge";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/State";
import { InvestigationDetail } from "../features/investigation/InvestigationDetail";
import { money, pct } from "../lib/format";
import { riskTone, statusTone } from "../lib/status";
import { useAuditra } from "../hooks/useAuditra";
import type { ReconciliationCase } from "../types/auditra";

export function InvestigationsPage() {
  const { audit, selectedCase, selectCase, setActivePage } = useAuditra();
  const cases = audit?.controller_run.cases ?? [];
  const exceptionCases = cases.filter((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status));

  if (!audit) {
    return <EmptyState title="No investigations yet" detail="Run reconciliation to create cases with evidence, tool traces and verification output." />;
  }

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader title="Investigation Queue" kicker={`${exceptionCases.length} exception-first cases`} />
        <DataTable rows={exceptionCases.length ? exceptionCases : cases} columns={columns} getRowId={(row) => row.case_id} onRowClick={(row) => selectCase(row.case_id)} initialPageSize={10} />
      </Card>
      <InvestigationDetail
        item={selectedCase}
        onGraph={() => setActivePage("evidence-graph")}
        onRecords={() => setActivePage("world-explorer")}
        onReview={() => setActivePage("human-review")}
      />
    </div>
  );
}

const columns: Column<ReconciliationCase>[] = [
  {
    key: "case",
    header: "Case",
    value: (row) => row.case_id,
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
    key: "impact",
    header: "Impact",
    value: (row) => money(row.decision.financial_impact),
    sortValue: (row) => Number(row.decision.financial_impact),
  },
  {
    key: "risk",
    header: "Risk",
    value: (row) => <Badge tone={riskTone(row.risk_score)}>{row.risk_score.toFixed(1)}</Badge>,
    sortValue: (row) => row.risk_score,
  },
  {
    key: "confidence",
    header: "Confidence",
    value: (row) => `${pct(row.decision.confidence_score)} / ${row.decision.confidence_band}`,
    sortValue: (row) => row.decision.confidence_score,
  },
];
