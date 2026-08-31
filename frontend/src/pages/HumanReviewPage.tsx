import { executionLabel } from "../lib/format";
import { useMemo, useState } from "react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { Textarea } from "../components/ui/Field";
import { EmptyState, SuccessState } from "../components/ui/State";
import { money } from "../lib/format";
import { riskTone, statusTone } from "../lib/status";
import { useAuditra } from "../hooks/useAuditra";
import type { ReconciliationCase, ReviewAction } from "../types/auditra";

export function HumanReviewPage() {
  const { audit, selectedCase, setSelectedCase, reviewCase, lastReviewEvent, isBusy } = useAuditra();
  const [note, setNote] = useState("Reviewed in Phase B demo workspace.");
  const cases = audit?.controller_run.cases ?? [];
  const rows = useMemo(
    () =>
      cases
        .filter((item) => ["HUMAN_REVIEW", "UNRESOLVED"].includes(item.status) || item.risk_score >= 28 || Number(item.decision.financial_impact) > 0)
        .sort((a, b) => b.risk_score - a.risk_score || Number(b.decision.financial_impact) - Number(a.decision.financial_impact)),
    [cases],
  );

  if (!audit) {
    return <EmptyState title="No human review queue" detail="Run reconciliation to produce cases requiring review." />;
  }

  const canReview = Boolean(selectedCase);
  const submit = (action: ReviewAction) => {
    if (selectedCase) void reviewCase(selectedCase.case_id, action, note);
  };

  return (
    <div className="space-y-5">
      {lastReviewEvent ? <SuccessState title={lastReviewEvent} detail="The backend recorded the review event for the current controller run." /> : null}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card>
          <SectionHeader title="Human Review Queue" kicker={`${rows.length} cases surfaced for reviewer action`} />
          <DataTable rows={rows} columns={columns} getRowId={(row) => row.case_id} onRowClick={setSelectedCase} />
        </Card>
        <Card>
          <SectionHeader title="Review Action" kicker={selectedCase?.case_id ?? "Select a case"} />
          {selectedCase ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge tone={statusTone(selectedCase.status)}>{selectedCase.status}</Badge>
                <Badge tone={riskTone(selectedCase.risk_score)}>Risk {selectedCase.risk_score.toFixed(1)}</Badge>
              </div>
              <div className="rounded-lg border border-line bg-slate-50 p-3 text-sm leading-6 text-muted">
                {selectedCase.decision.reason_codes.join(", ") || "No reason codes reported."}
              </div>
              <Textarea value={note} onChange={(event) => setNote(event.target.value)} />
            </div>
          ) : (
            <EmptyState title="No case selected" detail="Choose a queue item before recording a reviewer action." />
          )}
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <Button variant="success" disabled={!canReview || isBusy} onClick={() => submit("APPROVE")}>Approve</Button>
            <Button variant="danger" disabled={!canReview || isBusy} onClick={() => submit("REJECT")}>Reject</Button>
            <Button disabled={!canReview || isBusy} onClick={() => submit("MARK_UNRESOLVED")}>Mark Unresolved</Button>
          </div>
        </Card>
      </div>
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
    key: "ai",
    header: "AI",
    value: (row) => (row.ai_investigation ? <Badge tone="review">{executionLabel(row.ai_investigation.mode)}</Badge> : <Badge tone="muted">not invoked</Badge>),
    sortValue: (row) => row.ai_investigation?.mode ?? "",
  },
];
