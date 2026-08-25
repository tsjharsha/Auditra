import { useMutation, useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { auditraApi } from "../api/client";
import type {
  AnomalyMode,
  AuditWorldResult,
  ControllerComparison,
  FinancialWorldSpec,
  PageId,
  ReconciliationCase,
  ReviewAction,
  WorldBuildResult,
  WorldPreview,
} from "../types/auditra";

export const DEFAULT_PROMPT =
  "Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, 2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies.";

export const PROMPT_SUGGESTIONS = [
  "Indian e-commerce merchant with 500 orders, UPI and card payments, 2% platform fees, T+2 settlement, refunds and realistic reconciliation anomalies.",
  "SaaS merchant with 300 invoices, card payments, 2.5% fees, T+3 settlement, partial settlements and timing mismatches.",
  "Indian marketplace with 1000 orders, UPI, card and wallet payments, refunds, duplicates, fee mismatches and adversarial anomalies.",
];

export interface RunHistoryItem {
  runId: string;
  worldId?: string;
  datasetId: string;
  seed: number;
  mode: string;
  model: string;
  timestamp: string;
  records: number;
  accuracy?: number;
  f1?: number;
  humanReviewRate: number;
  aiInvocationRate: number;
}

export interface ControlledEvaluationSettings {
  recordCount: number;
  seed: number;
  anomalyMode: AnomalyMode;
  anomalyRates: Record<string, string>;
}

interface AuditraContextValue {
  activePage: PageId;
  setActivePage: (page: PageId) => void;
  prompt: string;
  setPrompt: (prompt: string) => void;
  seed: number;
  setSeed: (seed: number) => void;
  preview: WorldPreview | null;
  world: WorldBuildResult | null;
  audit: AuditWorldResult | null;
  comparison: ControllerComparison | null;
  selectedCase: ReconciliationCase | null;
  runHistory: RunHistoryItem[];
  lastReviewEvent: string | null;
  statusMessage: string;
  healthStatus: string;
  isBusy: boolean;
  busyLabel: string;
  error: unknown;
  previewWorld: () => Promise<WorldPreview>;
  buildWorld: () => Promise<WorldBuildResult>;
  buildWorldFromSpec: (spec: FinancialWorldSpec) => Promise<WorldBuildResult>;
  auditWorld: (worldOverride?: WorldBuildResult) => Promise<AuditWorldResult>;
  useDemoWorld: () => void;
  runFiveMinuteDemo: () => Promise<void>;
  breakController: (mode: AnomalyMode, recordCount?: number) => Promise<void>;
  runComparison: () => Promise<ControllerComparison>;
  runControlledEvaluation: (settings: ControlledEvaluationSettings) => Promise<AuditWorldResult>;
  selectCase: (caseId: string) => void;
  setSelectedCase: (item: ReconciliationCase | null) => void;
  reviewCase: (caseId: string, action: ReviewAction, note: string) => Promise<void>;
}

const AuditraContext = createContext<AuditraContextValue | null>(null);
const PAGE_IDS: PageId[] = [
  "home",
  "worlds",
  "audits",
  "review",
  "insights",
  "settings",
  "world-builder",
  "world-explorer",
  "reconciliation",
  "investigations",
  "evidence-graph",
  "human-review",
  "evaluation-lab",
  "controller-runs",
  "audit-trail",
];

export function AuditraProvider({ children }: { children: ReactNode }) {
  const [activePage, setActivePage] = useState<PageId>(() => pageFromUrl() ?? "home");
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [seed, setSeed] = useState(42);
  const [preview, setPreview] = useState<WorldPreview | null>(null);
  const [world, setWorld] = useState<WorldBuildResult | null>(null);
  const [audit, setAudit] = useState<AuditWorldResult | null>(null);
  const [comparison, setComparison] = useState<ControllerComparison | null>(null);
  const [selectedCase, setSelectedCase] = useState<ReconciliationCase | null>(null);
  const [runHistory, setRunHistory] = useState<RunHistoryItem[]>([]);
  const [lastReviewEvent, setLastReviewEvent] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Ready");
  const [error, setError] = useState<unknown>(null);
  const [manualBusyLabel, setManualBusyLabel] = useState("");
  const demoDeepLinkStarted = useRef(false);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: auditraApi.health,
    retry: 1,
    refetchInterval: 15000,
  });

  const previewMutation = useMutation({
    mutationFn: () => auditraApi.previewWorld(prompt, seed),
    onMutate: () => {
      setError(null);
      setStatusMessage("Understanding prompt");
    },
    onSuccess: (result) => {
      setPreview(result);
      setStatusMessage("Structured world preview ready");
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("World preview failed");
    },
  });

  const buildMutation = useMutation({
    mutationFn: () => auditraApi.buildWorld(prompt, seed),
    onMutate: () => {
      setError(null);
      setStatusMessage("Generating financial world");
    },
    onSuccess: (result) => {
      setWorld(result);
      setPreview(result);
      setAudit(null);
      setComparison(null);
      setSelectedCase(null);
      setActivePage("world-explorer");
      setStatusMessage(`Financial world created: ${result.world_id}`);
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("World generation failed");
    },
  });

  const buildSpecMutation = useMutation({
    mutationFn: (spec: FinancialWorldSpec) => auditraApi.buildWorldFromSpec(spec),
    onMutate: () => {
      setError(null);
      setStatusMessage("Generating edited financial world");
    },
    onSuccess: (result) => {
      setWorld(result);
      setPreview(result);
      setAudit(null);
      setComparison(null);
      setSelectedCase(null);
      setActivePage("world-explorer");
      setStatusMessage(`Financial world created: ${result.world_id}`);
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("Edited spec generation failed");
    },
  });

  const auditMutation = useMutation({
    mutationFn: (targetWorld: WorldBuildResult) => auditraApi.auditWorld(targetWorld.world_id),
    onMutate: () => {
      setError(null);
      setStatusMessage("Auditing financial world");
    },
    onSuccess: (result) => {
      setAudit(result);
      setWorld(result.world);
      setComparison(result.comparison);
      setSelectedCase(firstDifficultCase(result) ?? result.controller_run.cases[0] ?? null);
      appendRunHistory(result);
      setActivePage("reconciliation");
      setStatusMessage(result.survival_status);
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("Audit failed");
    },
  });

  const compareMutation = useMutation({
    mutationFn: () => auditraApi.compare({ dataset_id: world?.dataset_id }),
    onMutate: () => {
      setError(null);
      setStatusMessage("Comparing baseline and AI controller modes");
    },
    onSuccess: (result) => {
      setComparison(result);
      setAudit((current) => (current ? { ...current, comparison: result } : current));
      setStatusMessage("AI vs baseline comparison ready");
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("Comparison failed");
    },
  });

  const controlledMutation = useMutation({
    mutationFn: async (settings: ControlledEvaluationSettings) => {
      const spec = createControlledSpec(settings);
      const built = await auditraApi.buildWorldFromSpec(spec);
      return auditraApi.auditWorld(built.world_id);
    },
    onMutate: () => {
      setError(null);
      setStatusMessage("Running controlled evaluation world");
    },
    onSuccess: (result) => {
      setWorld(result.world);
      setPreview(result.world);
      setAudit(result);
      setComparison(result.comparison);
      setSelectedCase(firstDifficultCase(result) ?? result.controller_run.cases[0] ?? null);
      appendRunHistory(result);
      setActivePage("evaluation-lab");
      setStatusMessage(result.survival_status);
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("Controlled evaluation failed");
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ caseId, action, note }: { caseId: string; action: ReviewAction; note: string }) => {
      if (!audit) throw new Error("No controller run is available for review");
      return auditraApi.review(caseId, audit.controller_run.run_id, action, "demo_reviewer", note);
    },
    onSuccess: (result) => {
      setLastReviewEvent(`${result.action} recorded for ${result.case_id}`);
      setStatusMessage(`${result.action} recorded`);
    },
    onError: (err) => {
      setError(err);
      setStatusMessage("Review action failed");
    },
  });

  async function runFiveMinuteDemo() {
    setManualBusyLabel("Demo run");
    setError(null);
    setStatusMessage("Starting 5-minute demo");
    try {
      setPrompt(DEFAULT_PROMPT);
      setSeed(42);
      const previewResult = await auditraApi.previewWorld(DEFAULT_PROMPT, 42);
      setPreview(previewResult);
      setStatusMessage("Generating demo world");
      const built = await auditraApi.buildWorld(DEFAULT_PROMPT, 42);
      setWorld(built);
      setStatusMessage("Auditing demo world");
      const audited = await auditraApi.auditWorld(built.world_id);
      setAudit(audited);
      setComparison(audited.comparison);
      setSelectedCase(firstDifficultCase(audited) ?? audited.controller_run.cases[0] ?? null);
      appendRunHistory(audited);
      setActivePage("reconciliation");
      setStatusMessage("5-minute demo world is ready");
    } catch (err) {
      setError(err);
      setStatusMessage("Demo run failed");
      throw err;
    } finally {
      setManualBusyLabel("");
    }
  }

  async function breakController(mode: AnomalyMode, recordCount = 500) {
    setManualBusyLabel(`${mode} stress run`);
    setError(null);
    setStatusMessage(`Building ${mode.toLowerCase()} evaluation world`);
    try {
      const spec = createControlledSpec({
        recordCount,
        seed,
        anomalyMode: mode,
        anomalyRates: stressRatesFor(mode),
      });
      setPrompt(spec.prompt);
      const built = await auditraApi.buildWorldFromSpec(spec);
      setWorld(built);
      setPreview(built);
      setStatusMessage(`Auditing ${mode.toLowerCase()} world`);
      const audited = await auditraApi.auditWorld(built.world_id);
      setAudit(audited);
      setComparison(audited.comparison);
      setSelectedCase(firstDifficultCase(audited) ?? audited.controller_run.cases[0] ?? null);
      appendRunHistory(audited);
      setActivePage("evaluation-lab");
      setStatusMessage(audited.survival_status);
    } catch (err) {
      setError(err);
      setStatusMessage("Stress run failed");
      throw err;
    } finally {
      setManualBusyLabel("");
    }
  }

  function appendRunHistory(result: AuditWorldResult) {
    const run = result.controller_run;
    const evaluation = result.evaluation;
    setRunHistory((current) => [
      {
        runId: run.run_id,
        worldId: result.world.world_id,
        datasetId: run.dataset_id,
        seed: result.world.spec.seed,
        mode: result.world.spec.anomaly_mode,
        model: firstAiModel(run.cases),
        timestamp: run.started_at,
        records: run.metrics.transactions_processed,
        accuracy: evaluation.metrics.accuracy,
        f1: evaluation.metrics.f1,
        humanReviewRate: run.metrics.human_review_rate,
        aiInvocationRate: run.metrics.ai_invocation_rate,
      },
      ...current.filter((item) => item.runId !== run.run_id),
    ]);
  }

  function selectCase(caseId: string) {
    const next = audit?.controller_run.cases.find((item) => item.case_id === caseId) ?? null;
    setSelectedCase(next);
    if (next) setActivePage("investigations");
  }

  const isBusy =
    previewMutation.isPending ||
    buildMutation.isPending ||
    buildSpecMutation.isPending ||
    auditMutation.isPending ||
    compareMutation.isPending ||
    controlledMutation.isPending ||
    reviewMutation.isPending ||
    Boolean(manualBusyLabel);

  const busyLabel = previewMutation.isPending
    ? "Understanding"
    : buildMutation.isPending || buildSpecMutation.isPending
      ? "Generating"
      : auditMutation.isPending
        ? "Auditing"
        : compareMutation.isPending || controlledMutation.isPending
          ? "Evaluating"
          : reviewMutation.isPending
            ? "Reviewing"
            : manualBusyLabel;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") !== "1" || demoDeepLinkStarted.current) return;
    demoDeepLinkStarted.current = true;
    const targetPage = pageFromUrl();
    const stress = params.get("stress") === "1";
    void runFiveMinuteDemo().then(async () => {
      if (stress) {
        await breakController("ADVERSARIAL", 500);
      }
      if (targetPage) {
        setActivePage(targetPage);
      }
    });
  }, []);

  const value = useMemo<AuditraContextValue>(
    () => ({
      activePage,
      setActivePage,
      prompt,
      setPrompt,
      seed,
      setSeed,
      preview,
      world,
      audit,
      comparison,
      selectedCase,
      runHistory,
      lastReviewEvent,
      statusMessage,
      healthStatus: health.data?.status ?? (health.isError ? "offline" : "checking"),
      isBusy,
      busyLabel,
      error,
      previewWorld: () => previewMutation.mutateAsync(),
      buildWorld: () => buildMutation.mutateAsync(),
      buildWorldFromSpec: (spec) => buildSpecMutation.mutateAsync(spec),
      auditWorld: (worldOverride) => {
        const target = worldOverride ?? world;
        if (!target) return Promise.reject(new Error("Build a world before auditing"));
        return auditMutation.mutateAsync(target);
      },
      useDemoWorld: () => {
        setPrompt(DEFAULT_PROMPT);
        setSeed(42);
        setActivePage("home");
        setStatusMessage("Demo prompt loaded");
      },
      runFiveMinuteDemo,
      breakController,
      runComparison: () => compareMutation.mutateAsync(),
      runControlledEvaluation: (settings) => controlledMutation.mutateAsync(settings),
      selectCase,
      setSelectedCase,
      reviewCase: (caseId, action, note) => reviewMutation.mutateAsync({ caseId, action, note }).then(() => undefined),
    }),
    [
      activePage,
      audit,
      busyLabel,
      comparison,
      error,
      health.data?.status,
      health.isError,
      isBusy,
      lastReviewEvent,
      manualBusyLabel,
      preview,
      prompt,
      runHistory,
      seed,
      selectedCase,
      statusMessage,
      world,
    ],
  );

  return <AuditraContext.Provider value={value}>{children}</AuditraContext.Provider>;
}

export function useAuditra() {
  const context = useContext(AuditraContext);
  if (!context) throw new Error("useAuditra must be used inside AuditraProvider");
  return context;
}

function firstDifficultCase(result: AuditWorldResult) {
  return (
    result.controller_run.cases.find((item) => item.status === "HUMAN_REVIEW") ??
    result.controller_run.cases.find((item) => !["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"].includes(item.status)) ??
    null
  );
}

function firstAiModel(cases: ReconciliationCase[]) {
  return cases.find((item) => item.ai_investigation)?.ai_investigation?.model ?? "offline";
}

function pageFromUrl(): PageId | null {
  const params = new URLSearchParams(window.location.search);
  const page = params.get("page");
  const aliases: Record<string, PageId> = {
    home: "home",
    worlds: "worlds",
    "world-builder": "worlds",
    "world-explorer": "worlds",
    audits: "audits",
    reconciliation: "audits",
    review: "review",
    investigations: "review",
    "human-review": "review",
    "evidence-graph": "review",
    insights: "insights",
    "evaluation-lab": "insights",
    "controller-runs": "insights",
    "audit-trail": "insights",
    settings: "settings",
  };
  const resolved = page ? aliases[page] ?? page : null;
  return PAGE_IDS.includes(resolved as PageId) ? (resolved as PageId) : null;
}

function createControlledSpec(settings: ControlledEvaluationSettings): FinancialWorldSpec {
  const prompt = `Evaluation lab world with ${settings.recordCount} orders and ${settings.anomalyMode.toLowerCase()} controlled anomaly rates.`;
  return {
    prompt,
    world_name: "Evaluation Lab Commerce",
    merchant_name: "Evaluation Lab Commerce",
    country: "IN",
    record_count: settings.recordCount,
    seed: settings.seed,
    currencies: ["INR"],
    payment_methods: ["UPI", "CARD"],
    fee_rate: "0.0200",
    fixed_fee: "0.00",
    settlement_delay_days: 2,
    refund_rate: "0.0800",
    partial_settlement_rate: settings.anomalyRates.PARTIAL_SETTLEMENT ?? "0.0300",
    anomaly_mode: settings.anomalyMode,
    anomaly_rates: settings.anomalyRates,
    temporal_rules: {},
    relationships: [],
    constraints: ["evaluation_lab_controlled_rates"],
    start_at: "2026-01-05T09:30:00+00:00",
    source: "phase_b_evaluation_lab",
    understanding_source: "manual_ui_spec",
    version: 1,
  };
}

function stressRatesFor(mode: AnomalyMode): Record<string, string> {
  if (mode === "CHAOS") {
    return {
      AMOUNT_MISMATCH: "0.1000",
      MISSING_SETTLEMENT: "0.0900",
      DUPLICATE_PAYMENT: "0.0600",
      FEE_MISMATCH: "0.0800",
      REFUND_MISMATCH: "0.0700",
      PARTIAL_SETTLEMENT: "0.0800",
      TIMING_MISMATCH: "0.0800",
      CONFLICTING_EVIDENCE: "0.0800",
      CURRENCY_MISMATCH: "0.0400",
      ENTITY_LINK_FAILURE: "0.0400",
    };
  }
  if (mode === "ADVERSARIAL") {
    return {
      AMOUNT_MISMATCH: "0.0700",
      MISSING_SETTLEMENT: "0.0600",
      DUPLICATE_PAYMENT: "0.0500",
      FEE_MISMATCH: "0.0500",
      REFUND_MISMATCH: "0.0500",
      PARTIAL_SETTLEMENT: "0.0500",
      TIMING_MISMATCH: "0.0500",
      CONFLICTING_EVIDENCE: "0.0500",
      CURRENCY_MISMATCH: "0.0300",
      ENTITY_LINK_FAILURE: "0.0300",
    };
  }
  if (mode === "STRESSED") {
    return {
      AMOUNT_MISMATCH: "0.0400",
      MISSING_SETTLEMENT: "0.0350",
      DUPLICATE_PAYMENT: "0.0250",
      FEE_MISMATCH: "0.0250",
      REFUND_MISMATCH: "0.0200",
      PARTIAL_SETTLEMENT: "0.0350",
      TIMING_MISMATCH: "0.0300",
      CONFLICTING_EVIDENCE: "0.0200",
    };
  }
  return {
    AMOUNT_MISMATCH: "0.0050",
    MISSING_SETTLEMENT: "0.0020",
    DUPLICATE_PAYMENT: "0.0020",
    FEE_MISMATCH: "0.0030",
    REFUND_MISMATCH: "0.0020",
    PARTIAL_SETTLEMENT: "0.0030",
    TIMING_MISMATCH: "0.0020",
    CONFLICTING_EVIDENCE: "0.0010",
  };
}
