import { ClipboardCheck, Workflow } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { Metric, MetricGrid } from "../components/ui/Metric";
import { EmptyState } from "../components/ui/State";
import { WorldRecordExplorer } from "../features/world/WorldRecordExplorer";
import { compact, money } from "../lib/format";
import { useAuditra } from "../hooks/useAuditra";

export function WorldExplorerPage() {
  const { world, auditWorld, setActivePage, isBusy } = useAuditra();

  if (!world) {
    return (
      <EmptyState
        title="No world to explore"
        detail="Generate a financial world first, then inspect source records and validation output here."
        action={<Button variant="primary" icon={<Workflow className="h-4 w-4" />} onClick={() => setActivePage("world-builder")}>Open World Builder</Button>}
      />
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader
          title={world.summary.merchant}
          kicker={`${world.world_id} / ${world.dataset_id}`}
          action={<Button variant="primary" icon={<ClipboardCheck className="h-4 w-4" />} disabled={isBusy} onClick={() => void auditWorld(world)}>Audit This World</Button>}
        />
        <MetricGrid>
          <Metric label="Orders" value={compact(world.summary.orders)} />
          <Metric label="Payments" value={compact(world.summary.payments)} />
          <Metric label="Settlements" value={compact(world.summary.settlements)} />
          <Metric label="Refunds" value={compact(world.summary.refunds)} />
          <Metric label="Payment Volume" value={money(world.summary.payment_volume)} />
          <Metric label="Anomalies" value={compact(world.summary.anomalies)} tone={world.summary.anomalies ? "warning" : "success"} />
        </MetricGrid>
      </Card>
      <WorldRecordExplorer world={world} />
    </div>
  );
}
