import { LockKeyhole, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import { API_BASE } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { EmptyState } from "../components/ui/State";
import { compact } from "../lib/format";
import { useAuditra } from "../hooks/useAuditra";

export function SettingsPage() {
  const { world, audit, healthStatus, statusMessage, comparison, runFiveMinuteDemo, isBusy } = useAuditra();

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
          <SectionHeader title="Workspace" kicker="The current environment Auditra is working inside" />
          <SettingRow label="API status" value={healthStatus} badge />
          <SettingRow label="Current status" value={statusMessage} />
          <SettingRow label="Active world" value={world?.summary.merchant ?? "No world yet"} />
          <SettingRow label="Dataset" value={world?.dataset_id ?? "No dataset yet"} />
          <div className="mt-4">
            <Button variant="primary" icon={<Workflow className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>
              Run demo workspace
            </Button>
          </div>
        </Card>

        <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
          <SectionHeader title="AI" kicker="A concise read on model-backed investigation activity" />
          <SettingRow label="Comparison ready" value={comparison ? "Yes" : "Not yet"} badge />
          <SettingRow label="AI-assisted cases" value={audit ? compact(audit.controller_run.metrics.ai_investigation_count) : "0"} />
          <SettingRow label="Review rate" value={audit ? `${(audit.controller_run.metrics.human_review_rate * 100).toFixed(1)}%` : "-"} />
          <div className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4 text-sm leading-6 text-indigo-900">
            Advanced AI benchmarking and stress modes now live under the Insights page.
          </div>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
          <SectionHeader title="Data" kicker="The current world and audit payload in product language" />
          {world ? (
            <div className="space-y-3">
              <SettingRow label="Merchant" value={world.summary.merchant} />
              <SettingRow label="Orders" value={compact(world.summary.orders)} />
              <SettingRow label="Payments" value={compact(world.summary.payments)} />
              <SettingRow label="Currencies" value={world.summary.currencies.join(" / ")} />
            </div>
          ) : (
            <EmptyState title="No data yet" detail="Create a world to see workspace-level data settings and summaries." />
          )}
        </Card>

        <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
          <SectionHeader title="Security" kicker="Trust, review, and audit-trail status for the current session" />
          <div className="grid gap-3">
            <SecurityItem icon={<ShieldCheck className="h-4 w-4" />} title="Reviewable decisions" detail={audit ? `${compact(audit.controller_run.cases.length)} controller decisions are available for review.` : "No controller decisions yet."} />
            <SecurityItem icon={<LockKeyhole className="h-4 w-4" />} title="Audit trail" detail={audit ? `${compact(audit.controller_run.audit_events.length)} audit events are available in this session.` : "No audit trail yet."} />
            <SecurityItem icon={<Sparkles className="h-4 w-4" />} title="Advanced diagnostics" detail="Technical metadata, investigation detail, and stress testing are available behind progressive disclosure instead of the primary workflow." />
          </div>
        </Card>
      </div>

      <Card className="rounded-[32px] border-white/70 bg-white/90 p-6">
        <SectionHeader title="Technical details" kicker="A small place for environment information that should not dominate the product UI" />
        <div className="grid gap-3 md:grid-cols-3">
          <SettingRow label="API base" value={API_BASE} />
          <SettingRow label="World ID" value={world?.world_id ?? "Not generated"} />
          <SettingRow label="Run ID" value={audit?.controller_run.run_id ?? "No audit run"} />
        </div>
      </Card>
    </div>
  );
}

function SettingRow({ label, value, badge = false }: { label: string; value: string; badge?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-line bg-slate-50/80 px-4 py-3">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {badge ? <Badge tone="muted">{value}</Badge> : <span className="text-sm font-semibold text-slate-950">{value}</span>}
    </div>
  );
}

function SecurityItem({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-line bg-slate-50/80 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
        <span className="text-indigo-600">{icon}</span>
        {title}
      </div>
      <div className="mt-2 text-sm leading-6 text-muted">{detail}</div>
    </div>
  );
}
