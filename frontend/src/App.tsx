import { lazy, Suspense } from "react";
import { AppShell } from "./components/AppShell";

const WarRoomPage = lazy(() => import("./pages/WarRoomPage").then((module) => ({ default: module.WarRoomPage })));

export function App() {
  return (
    <AppShell>
      <Suspense fallback={<div className="p-8 text-sm text-[#9a9792]">Booting matrix...</div>}>
        <WarRoomPage />
      </Suspense>
    </AppShell>
  );
}
