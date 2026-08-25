import { useMemo, useState } from "react";
import { ArrowRight, Search, ShieldAlert } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Card, SectionHeader } from "../../components/ui/Card";
import { type Column, DataTable } from "../../components/ui/DataTable";
import { Tabs } from "../../components/ui/Tabs";
import { EmptyState } from "../../components/ui/State";
import { compact, jsonPreview, money, shortId, titleCase } from "../../lib/format";
import { caseShortExplanation, caseTitle } from "../../lib/product";
import { riskTone, statusTone } from "../../lib/status";
import { SchemaRelationshipFlow } from "../graph/RelationshipFlow";
import type { PrimitiveRecord, ReconciliationCase, WorldBuildResult } from "../../types/auditra";

type ExplorerTab = "overview" | "activity" | "exceptions" | "relationships";

const tabs: Array<{ id: ExplorerTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "activity", label: "Activity" },
  { id: "exceptions", label: "Exceptions" },
  { id: "relationships", label: "Relationships" },
];

export function WorldRecordExplorer({
  world,
  cases = [],
  onSelectCase,
}: {
  world?: WorldBuildResult | null;
  cases?: ReconciliationCase[];
  onSelectCase?: (caseId: string) => void;
}) {
  const [active, setActive] = useState<ExplorerTab>("overview");
  const [detail, setDetail] = useState<PrimitiveRecord | null>(null);
  const records = world?.dataset?.records;
  const activityRows = useMemo(() => records?.payments ?? [], [records]);
  const exceptionRows = useMemo(
    () => cases.filter((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status)).slice(0, 8),
    [cases],
  );

  if (!world) {
    return <EmptyState title="No world generated" detail="Describe a financial world and Auditra will build one for you." />;
  }

  return (
    <div className="space-y-4">
      <Tabs
        tabs={tabs.map((tab) => ({
          ...tab,
          count:
            tab.id === "activity"
              ? activityRows.length
              : tab.id === "exceptions"
                ? exceptionRows.length
                : undefined,
        }))}
        active={active}
        onChange={setActive}
      />

      {active === "overview" ? <Overview world={world} /> : null}

      {active === "activity" ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <DataTable
            rows={activityRows}
            columns={activityColumns}
            getRowId={(row) => String(row.payment_id ?? JSON.stringify(row))}
            onRowClick={setDetail}
            emptyTitle="No payment activity"
          />
          <Card>
            <SectionHeader title="Transaction detail" kicker={detail ? String(detail.payment_id ?? "Selected payment") : "Choose a payment"} />
            {detail ? (
              <pre className="max-h-[520px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                {jsonPreview(detail, 2600)}
              </pre>
            ) : (
              <EmptyState title="No activity selected" detail="Open a transaction to inspect the generated record." />
            )}
          </Card>
        </div>
      ) : null}

      {active === "exceptions" ? (
        exceptionRows.length ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {exceptionRows.map((item) => (
              <button
                key={item.case_id}
                className="rounded-[24px] border border-line bg-white/90 p-5 text-left shadow-panel transition hover:-translate-y-0.5 hover:shadow-[0_18px_42px_rgba(15,23,42,0.08)]"
                onClick={() => onSelectCase?.(item.case_id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="grid h-10 w-10 place-items-center rounded-2xl bg-amber-50 text-amber-600">
                        <ShieldAlert className="h-5 w-5" />
                      </span>
                      <div>
                        <div className="text-sm font-semibold text-slate-950">{caseTitle(item)}</div>
                        <div className="text-sm text-muted">{shortId(item.payment_id, 26)}</div>
                      </div>
                    </div>
                    <p className="mt-4 text-sm leading-6 text-muted">{caseShortExplanation(item)}</p>
                  </div>
                  <Badge tone={statusTone(item.status)}>{titleCase(item.status)}</Badge>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Badge tone={riskTone(item.risk_score)}>Risk {item.risk_score.toFixed(1)}</Badge>
                  <Badge tone={Number(item.decision.financial_impact) > 0 ? "warning" : "muted"}>{money(item.decision.financial_impact)}</Badge>
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700">
                    Review case
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState title="No exceptions yet" detail="Run an audit to surface the transactions that need attention." />
        )
      ) : null}

      {active === "relationships" ? (
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
          <Card>
            <SectionHeader title="Relationship summary" kicker="How financial activity connects in this world" />
            <div className="space-y-3">
              {[
                ["Orders", compact(world.summary.orders)],
                ["Payments", compact(world.summary.payments)],
                ["Settlements", compact(world.summary.settlements)],
                ["Refunds", compact(world.summary.refunds)],
                ["Fee rules", compact(world.summary.fee_rules)],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between rounded-2xl border border-line bg-slate-50/80 px-4 py-3">
                  <span className="text-sm font-medium text-slate-700">{label}</span>
                  <span className="text-sm font-semibold text-slate-950">{value}</span>
                </div>
              ))}
              <div className="rounded-2xl border border-dashed border-line bg-white px-4 py-4 text-sm leading-6 text-muted">
                Orders lead to payments, payments lead to settlements, and refunds or fee rules explain the differences that matter.
              </div>
            </div>
          </Card>
          <SchemaRelationshipFlow model={world.relationship_model} />
        </div>
      ) : null}
    </div>
  );
}

function Overview({ world }: { world: WorldBuildResult }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
      <Card className="overflow-hidden bg-[linear-gradient(135deg,rgba(79,70,229,0.10),rgba(14,165,233,0.08),rgba(255,255,255,0.95))]">
        <SectionHeader title="Financial setup" kicker="A clear summary of the world Auditra built from your description" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[
            ["Merchant", world.summary.merchant],
            ["Financial activity", money(world.summary.payment_volume)],
            ["Orders", compact(world.summary.orders)],
            ["Payments", compact(world.summary.payments)],
            ["Settlements", compact(world.summary.settlements)],
            ["Refunds", compact(world.summary.refunds)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/80 bg-white/90 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
              <div className="mt-2 text-lg font-semibold tracking-tight text-slate-950">{value}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionHeader title="Health" kicker="Validation and anomaly coverage for this generated world" />
        <div className="space-y-3">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Validation</div>
            <div className="mt-2 text-lg font-semibold text-emerald-900">{world.validation.valid ? "Ready for audit" : "Needs attention"}</div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-line bg-slate-50/70 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Anomalies</div>
              <div className="mt-2 text-lg font-semibold text-slate-950">{compact(world.summary.anomalies)}</div>
            </div>
            <div className="rounded-2xl border border-line bg-slate-50/70 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Currencies</div>
              <div className="mt-2 text-lg font-semibold text-slate-950">{world.summary.currencies.join(" / ")}</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {world.validation.checks.slice(0, 5).map((check) => (
              <Badge key={check.check_id} tone={check.status === "PASSED" ? "success" : check.status === "WARNING" ? "warning" : "danger"}>
                {titleCase(check.check_id)}
              </Badge>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}

const activityColumns: Column<PrimitiveRecord>[] = [
  {
    key: "payment",
    header: "Payment",
    value: (row) => shortId(String(row.payment_id ?? ""), 26),
    sortValue: (row) => String(row.payment_id ?? ""),
    className: "font-mono text-xs",
  },
  {
    key: "order",
    header: "Order",
    value: (row) => shortId(String(row.order_id ?? ""), 24),
    sortValue: (row) => String(row.order_id ?? ""),
    className: "font-mono text-xs",
  },
  {
    key: "method",
    header: "Method",
    value: (row) => String(row.payment_method ?? "-"),
    sortValue: (row) => String(row.payment_method ?? ""),
  },
  {
    key: "amount",
    header: "Amount",
    value: (row) => money(row.amount as string | number | null),
    sortValue: (row) => Number(row.amount ?? 0),
  },
  {
    key: "captured",
    header: "Captured",
    value: (row) => shortId(String(row.captured_at ?? row.created_at ?? ""), 18),
    sortValue: (row) => String(row.captured_at ?? row.created_at ?? ""),
  },
  {
    key: "search",
    header: "Trace",
    value: () => <Search className="h-4 w-4 text-slate-400" />,
  },
];
