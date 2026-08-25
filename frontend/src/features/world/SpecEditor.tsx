import { useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Card, SectionHeader } from "../../components/ui/Card";
import { Field, Input, Select } from "../../components/ui/Field";
import { EmptyState } from "../../components/ui/State";
import type { AnomalyMode, FinancialWorldSpec } from "../../types/auditra";

const anomalyNames = [
  "AMOUNT_MISMATCH",
  "MISSING_SETTLEMENT",
  "DUPLICATE_PAYMENT",
  "FEE_MISMATCH",
  "REFUND_MISMATCH",
  "PARTIAL_SETTLEMENT",
  "TIMING_MISMATCH",
  "CONFLICTING_EVIDENCE",
];

export function SpecEditor({
  spec,
  onGenerate,
  disabled,
}: {
  spec?: FinancialWorldSpec | null;
  onGenerate: (spec: FinancialWorldSpec) => void;
  disabled?: boolean;
}) {
  const [draft, setDraft] = useState<FinancialWorldSpec | null>(spec ?? null);

  useEffect(() => {
    setDraft(spec ?? null);
  }, [spec]);

  if (!draft) {
    return <EmptyState title="No parsed specification" detail="Preview a prompt to edit the generated financial-world spec." />;
  }

  function update<K extends keyof FinancialWorldSpec>(key: K, value: FinancialWorldSpec[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  function updateRate(name: string, value: string) {
    setDraft((current) =>
      current
        ? {
            ...current,
            anomaly_rates: {
              ...current.anomaly_rates,
              [name]: value,
            },
          }
        : current,
    );
  }

  return (
    <Card>
      <SectionHeader
        title="Parsed Specification"
        kicker="Editable before deterministic generation"
        action={<Button disabled={disabled} variant="primary" onClick={() => draft && onGenerate(draft)}>Generate From Spec</Button>}
      />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Merchant">
          <Input value={draft.merchant_name} onChange={(event) => update("merchant_name", event.target.value)} />
        </Field>
        <Field label="Country">
          <Input value={draft.country} onChange={(event) => update("country", event.target.value)} />
        </Field>
        <Field label="Currency">
          <Input value={draft.currencies.join(", ")} onChange={(event) => update("currencies", splitTokens(event.target.value))} />
        </Field>
        <Field label="Orders">
          <Input
            type="number"
            min={10}
            max={10000}
            value={draft.record_count}
            onChange={(event) => update("record_count", Number(event.target.value))}
          />
        </Field>
        <Field label="Payment Methods">
          <Input value={draft.payment_methods.join(", ")} onChange={(event) => update("payment_methods", splitTokens(event.target.value))} />
        </Field>
        <Field label="Fee Rate">
          <Input value={draft.fee_rate} onChange={(event) => update("fee_rate", event.target.value)} />
        </Field>
        <Field label="Settlement">
          <Input
            type="number"
            min={0}
            max={30}
            value={draft.settlement_delay_days}
            onChange={(event) => update("settlement_delay_days", Number(event.target.value))}
          />
        </Field>
        <Field label="Refund Rate">
          <Input value={draft.refund_rate} onChange={(event) => update("refund_rate", event.target.value)} />
        </Field>
        <Field label="Anomaly Mode">
          <Select value={draft.anomaly_mode} onChange={(event) => update("anomaly_mode", event.target.value as AnomalyMode)}>
            {["NORMAL", "STRESSED", "ADVERSARIAL", "CHAOS"].map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Seed">
          <Input type="number" value={draft.seed} onChange={(event) => update("seed", Number(event.target.value))} />
        </Field>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {anomalyNames.map((name) => (
          <Field key={name} label={name}>
            <Input value={draft.anomaly_rates[name] ?? "0.0000"} onChange={(event) => updateRate(name, event.target.value)} />
          </Field>
        ))}
      </div>
    </Card>
  );
}

function splitTokens(value: string) {
  return value
    .split(",")
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
}
