import { AppShell } from "./components/AppShell";
import { useAuditra } from "./hooks/useAuditra";
import { AuditTrailPage } from "./pages/AuditTrailPage";
import { ControllerRunsPage } from "./pages/ControllerRunsPage";
import { EvaluationLabPage } from "./pages/EvaluationLabPage";
import { EvidenceGraphPage } from "./pages/EvidenceGraphPage";
import { HomePage } from "./pages/HomePage";
import { HumanReviewPage } from "./pages/HumanReviewPage";
import { InvestigationsPage } from "./pages/InvestigationsPage";
import { ReconciliationPage } from "./pages/ReconciliationPage";
import { WorldBuilderPage } from "./pages/WorldBuilderPage";
import { WorldExplorerPage } from "./pages/WorldExplorerPage";

export function App() {
  const { activePage } = useAuditra();

  return (
    <AppShell>
      {activePage === "home" ? <HomePage /> : null}
      {activePage === "world-builder" ? <WorldBuilderPage /> : null}
      {activePage === "world-explorer" ? <WorldExplorerPage /> : null}
      {activePage === "reconciliation" ? <ReconciliationPage /> : null}
      {activePage === "investigations" ? <InvestigationsPage /> : null}
      {activePage === "evidence-graph" ? <EvidenceGraphPage /> : null}
      {activePage === "human-review" ? <HumanReviewPage /> : null}
      {activePage === "evaluation-lab" ? <EvaluationLabPage /> : null}
      {activePage === "controller-runs" ? <ControllerRunsPage /> : null}
      {activePage === "audit-trail" ? <AuditTrailPage /> : null}
    </AppShell>
  );
}
