import { lazy, Suspense } from "react";
import { AppShell } from "./components/AppShell";
import { useAuditra } from "./hooks/useAuditra";
import { normalizePageId } from "./lib/navigation";

const HomePage = lazy(() => import("./pages/HomePage").then((module) => ({ default: module.HomePage })));
const WorldsPage = lazy(() => import("./pages/WorldsPage").then((module) => ({ default: module.WorldsPage })));
const AuditsPage = lazy(() => import("./pages/AuditsPage").then((module) => ({ default: module.AuditsPage })));
const ReviewPage = lazy(() => import("./pages/ReviewPage").then((module) => ({ default: module.ReviewPage })));
const InsightsPage = lazy(() => import("./pages/InsightsPage").then((module) => ({ default: module.InsightsPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));

export function App() {
  const { activePage } = useAuditra();
  const page = normalizePageId(activePage);

  return (
    <AppShell>
      <Suspense fallback={<div className="rounded-lg border border-white/10 bg-[#201f21] p-8 text-sm text-[#9a9792]">Opening workspace...</div>}>
        {page === "home" ? <HomePage /> : null}
        {page === "worlds" ? <WorldsPage /> : null}
        {page === "audits" ? <AuditsPage /> : null}
        {page === "review" ? <ReviewPage /> : null}
        {page === "insights" ? <InsightsPage /> : null}
        {page === "settings" ? <SettingsPage /> : null}
      </Suspense>
    </AppShell>
  );
}
