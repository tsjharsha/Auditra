import { AppShell } from "./components/AppShell";
import { useAuditra } from "./hooks/useAuditra";
import { normalizePageId } from "./lib/navigation";
import { AuditsPage } from "./pages/AuditsPage";
import { HomePage } from "./pages/HomePage";

export function App() {
  const { activePage } = useAuditra();
  const page = normalizePageId(activePage);

  return (
    <AppShell>
      {page === "home" ? <HomePage /> : null}
      {page === "audits" ? <AuditsPage /> : null}
    </AppShell>
  );
}
