import { AppShell } from "./components/AppShell";
import { useAuditra } from "./hooks/useAuditra";
import { normalizePageId } from "./lib/navigation";
import { AuditsPage } from "./pages/AuditsPage";
import { HomePage } from "./pages/HomePage";
import { InsightsPage } from "./pages/InsightsPage";
import { ReviewPage } from "./pages/ReviewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { WorldsPage } from "./pages/WorldsPage";

export function App() {
  const { activePage } = useAuditra();
  const page = normalizePageId(activePage);

  return (
    <AppShell>
      {page === "home" ? <HomePage /> : null}
      {page === "worlds" ? <WorldsPage /> : null}
      {page === "audits" ? <AuditsPage /> : null}
      {page === "review" ? <ReviewPage /> : null}
      {page === "insights" ? <InsightsPage /> : null}
      {page === "settings" ? <SettingsPage /> : null}
    </AppShell>
  );
}
