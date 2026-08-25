import { useMemo, useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import { type Column, DataTable } from "../../components/ui/DataTable";
import { Tabs } from "../../components/ui/Tabs";
import { EmptyState } from "../../components/ui/State";
import { compact, jsonPreview, money, shortId, titleCase } from "../../lib/format";
import type { PrimitiveRecord, VisibleDataset, WorldBuildResult } from "../../types/auditra";

type EntityTab = "overview" | "orders" | "payments" | "settlements" | "refunds" | "fees" | "anomalies";
type RecordTab = "orders" | "payments" | "settlements" | "refunds";

const tabs: Array<{ id: EntityTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "orders", label: "Orders" },
  { id: "payments", label: "Payments" },
  { id: "settlements", label: "Settlements" },
  { id: "refunds", label: "Refunds" },
  { id: "fees", label: "Fees" },
  { id: "anomalies", label: "Anomalies" },
];

export function WorldRecordExplorer({ world }: { world?: WorldBuildResult | null }) {
  const [active, setActive] = useState<EntityTab>("overview");
  const [detail, setDetail] = useState<PrimitiveRecord | null>(null);
  const records = world?.dataset?.records;

  const tabCounts = tabs.map((tab) => ({
    ...tab,
    count:
      tab.id === "overview"
        ? undefined
        : tab.id === "fees"
          ? records?.fee_rules.length
          : tab.id === "anomalies"
            ? world?.summary.anomalies
            : recordRowsFor(tab.id, records).length,
  }));

  const tableRows = useMemo(() => {
    return recordRowsFor(active, records);
  }, [active, records]);

  if (!world) {
    return <EmptyState title="No world generated" detail="Build a financial world to inspect records, schema and anomaly mix." />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="min-w-0 space-y-4">
        <Tabs tabs={tabCounts} active={active} onChange={setActive} />
        {active === "overview" ? <Overview world={world} /> : null}
        {active === "anomalies" ? <AnomalyPanel world={world} /> : null}
        {!["overview", "anomalies"].includes(active) ? (
          <DataTable
            rows={tableRows}
            columns={columnsFor(active)}
            getRowId={(row) => String(row[primaryKeyFor(active)] ?? JSON.stringify(row))}
            onRowClick={setDetail}
            emptyTitle={`No ${active} records`}
          />
        ) : null}
      </div>
      <Card>
        <SectionHeader title="Record Detail" kicker={detail ? String(detail[primaryKeyFor(active)] ?? "selected record") : "Click a row"} />
        {detail ? (
          <>
            <div className="mb-3 flex flex-wrap gap-2">
              {Object.entries(detail)
                .slice(0, 4)
                .map(([key, value]) => (
                  <Badge key={key} tone="muted">
                    {key}: {shortId(String(value), 20)}
                  </Badge>
                ))}
            </div>
            <pre className="max-h-[520px] overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
              {jsonPreview(detail, 2600)}
            </pre>
          </>
        ) : (
          <EmptyState title="No record selected" detail="Search, sort and open a generated source record." />
        )}
      </Card>
    </div>
  );
}

function Overview({ world }: { world: WorldBuildResult }) {
  const summary = world.summary;
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {[
        ["Merchant", summary.merchant],
        ["Payment volume", money(summary.payment_volume)],
        ["Orders", compact(summary.orders)],
        ["Payments", compact(summary.payments)],
        ["Settlements", compact(summary.settlements)],
        ["Refunds", compact(summary.refunds)],
        ["Fee", summary.fee],
        ["Settlement", summary.settlement],
        ["Currencies", summary.currencies.join(" / ")],
      ].map(([label, value]) => (
        <Card key={label}>
          <div className="text-xs font-bold uppercase text-muted">{label}</div>
          <div className="mt-2 text-xl font-bold text-ink">{value}</div>
        </Card>
      ))}
    </div>
  );
}

function AnomalyPanel({ world }: { world: WorldBuildResult }) {
  const entries = Object.entries(world.summary.anomaly_mix);
  return (
    <Card>
      <SectionHeader title="Controlled Anomalies" kicker="Counts are reported as aggregate evaluation setup, not per-record controller labels." />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {entries.map(([label, count]) => (
          <div key={label} className="rounded-lg border border-line bg-slate-50 p-3">
            <div className="text-xs font-bold uppercase text-muted">{titleCase(label)}</div>
            <div className="mt-2 text-2xl font-black text-ink">{count}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {world.validation.checks.map((check) => (
          <Badge key={check.check_id} tone={check.status === "PASSED" ? "success" : check.status === "WARNING" ? "warning" : "danger"}>
            {check.check_id}: {check.status}
          </Badge>
        ))}
      </div>
    </Card>
  );
}

function columnsFor(active: EntityTab): Column<PrimitiveRecord>[] {
  if (active === "orders") {
    return [
      col("order_id", "Order"),
      col("merchant_id", "Merchant"),
      col("customer_id", "Customer"),
      moneyCol("amount", "Amount"),
      col("currency", "Currency"),
      col("created_at", "Created"),
    ];
  }
  if (active === "payments") {
    return [
      col("payment_id", "Payment"),
      col("order_id", "Order"),
      col("payment_method", "Method"),
      moneyCol("amount", "Amount"),
      col("currency", "Currency"),
      col("captured_at", "Captured"),
    ];
  }
  if (active === "settlements") {
    return [
      col("settlement_id", "Settlement"),
      col("payment_id", "Payment"),
      col("batch_id", "Batch"),
      moneyCol("amount", "Amount"),
      col("currency", "Currency"),
      col("settled_at", "Settled"),
    ];
  }
  if (active === "refunds") {
    return [
      col("refund_id", "Refund"),
      col("payment_id", "Payment"),
      moneyCol("amount", "Amount"),
      col("currency", "Currency"),
      col("reason", "Reason"),
      col("refunded_at", "Refunded"),
    ];
  }
  return [
    col("fee_rule_id", "Fee Rule"),
    col("merchant_id", "Merchant"),
    col("currency", "Currency"),
    col("percent_bps", "BPS"),
    moneyCol("fixed_fee", "Fixed"),
    col("active_from", "Active From"),
  ];
}

function recordRowsFor(tab: EntityTab, records: VisibleDataset["records"] | undefined): PrimitiveRecord[] {
  if (!records || tab === "overview" || tab === "anomalies") return [];
  if (tab === "fees") return records.fee_rules;
  return records[tab as RecordTab] ?? [];
}

function col(key: string, header: string): Column<PrimitiveRecord> {
  return {
    key,
    header,
    value: (row) => shortId(String(row[key] ?? ""), 30),
    sortValue: (row) => String(row[key] ?? ""),
    className: key.endsWith("_id") ? "font-mono text-xs" : "",
  };
}

function moneyCol(key: string, header: string): Column<PrimitiveRecord> {
  return {
    key,
    header,
    value: (row) => money(String(row[key] ?? "")),
    sortValue: (row) => Number(row[key] ?? 0),
  };
}

function primaryKeyFor(active: EntityTab) {
  return {
    overview: "dataset_id",
    orders: "order_id",
    payments: "payment_id",
    settlements: "settlement_id",
    refunds: "refund_id",
    fees: "fee_rule_id",
    anomalies: "check_id",
  }[active];
}
