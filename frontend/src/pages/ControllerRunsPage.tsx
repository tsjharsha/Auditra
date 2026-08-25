import { Activity, PlayCircle } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { type Column, DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/State";
import { pct, shortId } from "../lib/format";
import { useAuditra, type RunHistoryItem } from "../hooks/useAuditra";

export function ControllerRunsPage() {
  const { runHistory, audit, setActivePage, runFiveMinuteDemo, isBusy } = useAuditra();

  if (!runHistory.length) {
    return (
      <EmptyState
        title="No controller runs"
        detail="Run the demo or audit a generated world to capture controller history in this session."
        action={<Button variant="primary" icon={<PlayCircle className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>Run 5-Minute Demo</Button>}
      />
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader
          title="Controller Runs"
          kicker={`${runHistory.length} run${runHistory.length === 1 ? "" : "s"} in the current session`}
          action={<Button icon={<Activity className="h-4 w-4" />} disabled={!audit} onClick={() => setActivePage("reconciliation")}>Open Current Run</Button>}
        />
        <DataTable rows={runHistory} columns={columns} getRowId={(row) => row.runId} onRowClick={() => setActivePage("reconciliation")} />
      </Card>
    </div>
  );
}

const columns: Column<RunHistoryItem>[] = [
  {
    key: "run",
    header: "Run",
    value: (row) => shortId(row.runId, 22),
    sortValue: (row) => row.runId,
    className: "font-mono text-xs",
  },
  {
    key: "world",
    header: "World",
    value: (row) => row.worldId ?? "-",
    sortValue: (row) => row.worldId ?? "",
    className: "font-mono text-xs",
  },
  {
    key: "records",
    header: "Records",
    value: (row) => row.records,
    sortValue: (row) => row.records,
  },
  {
    key: "mode",
    header: "Mode",
    value: (row) => <Badge tone={row.mode === "CHAOS" || row.mode === "ADVERSARIAL" ? "warning" : "info"}>{row.mode}</Badge>,
    sortValue: (row) => row.mode,
  },
  {
    key: "accuracy",
    header: "Accuracy",
    value: (row) => (row.accuracy === undefined ? "-" : pct(row.accuracy)),
    sortValue: (row) => row.accuracy ?? 0,
  },
  {
    key: "f1",
    header: "F1",
    value: (row) => (row.f1 === undefined ? "-" : pct(row.f1)),
    sortValue: (row) => row.f1 ?? 0,
  },
  {
    key: "review",
    header: "Human Review",
    value: (row) => pct(row.humanReviewRate),
    sortValue: (row) => row.humanReviewRate,
  },
  {
    key: "model",
    header: "AI Model",
    value: (row) => row.model,
    sortValue: (row) => row.model,
  },
];
