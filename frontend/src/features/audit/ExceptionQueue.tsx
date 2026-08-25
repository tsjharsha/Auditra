import { useMemo, useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import { type Column, DataTable } from "../../components/ui/DataTable";
import { Tabs } from "../../components/ui/Tabs";
import { money, pct } from "../../lib/format";
import { riskTone, statusTone } from "../../lib/status";
import type { ReconciliationCase } from "../../types/auditra";

type FilterId = "all" | "high-risk" | "high-value" | "ai" | "review" | "unresolved";

const filters: Array<{ id: FilterId; label: string }> = [
  { id: "all", label: "All" },
  { id: "high-risk", label: "High risk" },
  { id: "high-value", label: "High value" },
  { id: "ai", label: "AI investigated" },
  { id: "review", label: "Human review" },
  { id: "unresolved", label: "Unresolved" },
];

export function ExceptionQueue({
  cases,
  onSelect,
}: {
  cases: ReconciliationCase[];
  onSelect: (caseId: string) => void;
}) {
  const [filter, setFilter] = useState<FilterId>("all");
  const exceptionCases = cases.filter((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status));
  const rows = useMemo(() => {
    return exceptionCases
      .filter((item) => {
        if (filter === "high-risk") return item.risk_score >= 28;
        if (filter === "high-value") return Number(item.decision.financial_impact) >= 500;
        if (filter === "ai") return Boolean(item.ai_investigation);
        if (filter === "review") return item.status === "HUMAN_REVIEW";
        if (filter === "unresolved") return item.status === "UNRESOLVED";
        return true;
      })
      .sort((a, b) => b.risk_score - a.risk_score || Number(b.decision.financial_impact) - Number(a.decision.financial_impact));
  }, [exceptionCases, filter]);

  return (
    <Card>
      <SectionHeader
        title="Exception Queue"
        kicker={`${exceptionCases.length} exceptions from ${cases.length} audited transactions`}
        action={<Button onClick={() => setFilter("all")}>Clear Filters</Button>}
      />
      <Tabs
        tabs={filters.map((item) => ({ ...item, count: countFor(item.id, exceptionCases) }))}
        active={filter}
        onChange={setFilter}
      />
      <div className="mt-4">
        <DataTable rows={rows} columns={columns} getRowId={(row) => row.case_id} onRowClick={(row) => onSelect(row.case_id)} emptyTitle="No exceptions match this filter" />
      </div>
    </Card>
  );
}

const columns: Column<ReconciliationCase>[] = [
  {
    key: "payment",
    header: "Transaction",
    value: (row) => row.payment_id,
    sortValue: (row) => row.payment_id,
    className: "font-mono text-xs",
  },
  {
    key: "type",
    header: "Type",
    value: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
    sortValue: (row) => row.status,
  },
  {
    key: "difference",
    header: "Difference",
    value: (row) => row.decision.difference ?? "-",
    sortValue: (row) => Number(row.decision.difference ?? 0),
  },
  {
    key: "impact",
    header: "Financial Impact",
    value: (row) => money(row.decision.financial_impact),
    sortValue: (row) => Number(row.decision.financial_impact ?? 0),
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
  {
    key: "status",
    header: "AI",
    value: (row) => (row.ai_investigation ? <Badge tone="review">{row.ai_investigation.mode}</Badge> : <Badge tone="muted">not needed</Badge>),
    sortValue: (row) => row.ai_investigation?.mode ?? "",
  },
];

function countFor(filter: FilterId, cases: ReconciliationCase[]) {
  if (filter === "all") return cases.length;
  if (filter === "high-risk") return cases.filter((item) => item.risk_score >= 28).length;
  if (filter === "high-value") return cases.filter((item) => Number(item.decision.financial_impact) >= 500).length;
  if (filter === "ai") return cases.filter((item) => item.ai_investigation).length;
  if (filter === "review") return cases.filter((item) => item.status === "HUMAN_REVIEW").length;
  return cases.filter((item) => item.status === "UNRESOLVED").length;
}
