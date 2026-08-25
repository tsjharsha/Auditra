import { BarChart3, ExternalLink, Workflow } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/State";
import { AuditProgress } from "../features/audit/AuditProgress";
import { ControllerDashboard } from "../features/audit/ControllerDashboard";
import { ExceptionQueue } from "../features/audit/ExceptionQueue";
import { money, pct } from "../lib/format";
import { riskTone, statusTone } from "../lib/status";
import { useAuditra } from "../hooks/useAuditra";
import type { ReconciliationCase } from "../types/auditra";

export function ReconciliationPage() {
  const { audit, world, isBusy, auditWorld, runComparison, selectCase, setActivePage, comparison } = useAuditra();

  if (!audit) {
    return (
      <EmptyState
        title="No reconciliation run"
        detail={world ? "Audit the current financial world to create controller decisions." : "Build a financial world before running reconciliation."}
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" disabled={!world || isBusy} icon={<Workflow className="h-4 w-4" />} onClick={() => void auditWorld()}>
              Audit Current World
            </Button>
            <Button onClick={() => setActivePage("world-builder")}>Open World Builder</Button>
          </div>
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      <AuditProgress audit={audit} running={isBusy} />
      <ControllerDashboard audit={audit} comparison={comparison} compareDisabled={isBusy} onCompare={() => void runComparison()} />
      <ExceptionQueue cases={audit.controller_run.cases} onSelect={selectCase} />
      <Card>
        <SectionHeader
          title="All Reconciliation Cases"
          kicker={`${audit.controller_run.cases.length} controller decisions`}
          action={<Button icon={<BarChart3 className="h-4 w-4" />} onClick={() => setActivePage("evaluation-lab")}>Evaluation Lab</Button>}
        />
        <DataTable rows={audit.controller_run.cases} columns={caseColumns} getRowId={(row) => row.case_id} onRowClick={(row) => selectCase(row.case_id)} />
      </Card>
    </div>
  );
}

const caseColumns: Column<ReconciliationCase>[] = [
  {
    key: "case",
    header: "Case",
    value: (row) => row.case_id,
    sortValue: (row) => row.case_id,
    className: "font-mono text-xs",
  },
  {
    key: "payment",
    header: "Payment",
    value: (row) => row.payment_id,
    sortValue: (row) => row.payment_id,
    className: "font-mono text-xs",
  },
  {
    key: "status",
    header: "Status",
    value: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
    sortValue: (row) => row.status,
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
    value: (row) => pct(row.decision.confidence_score),
    sortValue: (row) => row.decision.confidence_score,
  },
  {
    key: "impact",
    header: "Impact",
    value: (row) => money(row.decision.financial_impact),
    sortValue: (row) => Number(row.decision.financial_impact),
  },
  {
    key: "evidence",
    header: "Evidence",
    value: (row) => (
      <span className="inline-flex items-center gap-1">
        <ExternalLink className="h-3.5 w-3.5" />
        {row.evidence.length}
      </span>
    ),
    sortValue: (row) => row.evidence.length,
  },
];
