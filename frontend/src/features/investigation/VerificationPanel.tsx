import { CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Card, SectionHeader } from "../../components/ui/Card";
import type { InvariantResult, VerificationResult } from "../../types/auditra";

export function VerificationPanel({
  verification,
  invariants,
}: {
  verification?: VerificationResult | null;
  invariants: InvariantResult[];
}) {
  const failedInvariants = invariants.filter((item) => item.status !== "PASSED");
  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Deterministic Verification" />
        <div className="space-y-2">
          {(verification?.checks ?? []).map((check) => (
            <div key={check.check} className="flex items-start justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-bold text-ink">
                  {check.passed ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-rose" />}
                  {check.check}
                </div>
                <div className="mt-1 text-sm text-muted">{check.detail}</div>
              </div>
              <Badge tone={check.passed ? "success" : "danger"}>{check.passed ? "passed" : "failed"}</Badge>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <SectionHeader title="Invariant Exceptions" kicker={failedInvariants.length ? `${failedInvariants.length} non-passing checks` : "All applicable controls passed"} />
        <div className="space-y-2">
          {(failedInvariants.length ? failedInvariants : invariants.slice(0, 6)).map((item) => (
            <div key={item.rule_id} className="rounded-lg border border-line bg-white p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="font-mono text-xs font-bold text-ink">{item.rule_id}</div>
                <Badge tone={item.status === "PASSED" ? "success" : item.status === "FAILED" ? "danger" : "warning"}>{item.status}</Badge>
              </div>
              <div className="mt-2 text-sm text-muted">{item.reason}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
