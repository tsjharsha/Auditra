import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, Code2, Play, RefreshCw, Shield, Terminal, Zap } from "lucide-react";

const API_BASE = import.meta.env.VITE_AUDITRA_API_BASE ?? "http://127.0.0.1:8002";

type LoopPhase = "idle" | "running" | "variance" | "prompting" | "patching" | "verified" | "failed";

interface VarianceInfo {
  failed_scenario: { tx_id: string; amount_str: string; is_international: boolean };
  target_output: Record<string, string>;
  expected_output: Record<string, string>;
  variances: Record<string, { expected: string; actual: string }>;
  passed_before_fail: number;
}

interface LogEntry {
  id: number;
  timestamp: string;
  type: "info" | "error" | "success" | "warning" | "ai";
  message: string;
}

export function WarRoomPage() {
  const [phase, setPhase] = useState<LoopPhase>("idle");
  const [sourceCode, setSourceCode] = useState<string>("");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [iteration, setIteration] = useState(0);
  const [progress, setProgress] = useState({ passed: 0, total: 0 });
  const [variance, setVariance] = useState<VarianceInfo | null>(null);
  const [certificate, setCertificate] = useState<any>(null);
  const [changedLines, setChangedLines] = useState<number[]>([]);
  const [scenarioCount, setScenarioCount] = useState(1000);
  const logRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const logIdRef = useRef(0);

  const now = () => new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const addLog = useCallback((type: LogEntry["type"], message: string) => {
    const entry: LogEntry = { id: logIdRef.current++, timestamp: now(), type, message };
    setLogs(prev => [...prev, entry]);
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  // Fetch initial source on mount
  useEffect(() => {
    fetch(`${API_BASE}/verification/source`).then(r => r.json()).then(d => setSourceCode(d.code)).catch(() => {});
  }, []);

  const resetTarget = async () => {
    const resp = await fetch(`${API_BASE}/verification/reset`, { method: "POST" });
    const data = await resp.json();
    setSourceCode(data.code);
    setPhase("idle");
    setLogs([]);
    setIteration(0);
    setProgress({ passed: 0, total: 0 });
    setVariance(null);
    setCertificate(null);
    setChangedLines([]);
    logIdRef.current = 0;
  };

  const startVerification = () => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    setPhase("running");
    setLogs([]);
    setIteration(0);
    setProgress({ passed: 0, total: 0 });
    setVariance(null);
    setCertificate(null);
    setChangedLines([]);
    logIdRef.current = 0;

    addLog("info", `Initiating Zero-Trust Verification Matrix with ${scenarioCount} adversarial scenarios...`);

    const es = new EventSource(`${API_BASE}/verification/stream?scenarios=${scenarioCount}`);
    eventSourceRef.current = es;

    es.addEventListener("source", (e) => {
      const d = JSON.parse(e.data);
      setSourceCode(d.code);
      addLog("info", `Target service loaded: ${d.path}`);
    });

    es.addEventListener("iteration_start", (e) => {
      const d = JSON.parse(e.data);
      setIteration(d.iteration);
      setProgress({ passed: 0, total: scenarioCount });
      setPhase("running");
      addLog("info", `--- ITERATION ${d.iteration} --- Launching ${scenarioCount} synthetic transactions...`);
    });

    es.addEventListener("progress", (e) => {
      const d = JSON.parse(e.data);
      setProgress({ passed: d.passed, total: d.total });
    });

    es.addEventListener("variance_detected", (e) => {
      const d = JSON.parse(e.data) as VarianceInfo;
      setVariance(d);
      setPhase("variance");
      addLog("error", `VARIANCE DETECTED on ${d.failed_scenario.tx_id} after ${d.passed_before_fail} passed`);
      const vKeys = Object.keys(d.variances);
      for (const k of vKeys) {
        addLog("error", `  ${k}: expected ${d.variances[k].expected} | actual ${d.variances[k].actual}`);
      }
    });

    es.addEventListener("prompting_ai", (e) => {
      setPhase("prompting");
      addLog("ai", "Sending failure fingerprint to IBM Bob 2.0...");
      addLog("ai", "Requesting autonomous code patch...");
    });

    es.addEventListener("patch_applied", (e) => {
      const d = JSON.parse(e.data);
      setPhase("patching");

      // Detect changed lines
      const oldLines = sourceCode.split("\n");
      const newLines = d.new_code.split("\n");
      const changed: number[] = [];
      const maxLen = Math.max(oldLines.length, newLines.length);
      for (let i = 0; i < maxLen; i++) {
        if (oldLines[i] !== newLines[i]) changed.push(i);
      }
      setChangedLines(changed);
      setSourceCode(d.new_code);
      addLog("success", "IBM Bob 2.0 applied code patch. Restarting matrix...");
    });

    es.addEventListener("iteration_passed", (e) => {
      const d = JSON.parse(e.data);
      setProgress({ passed: d.passed, total: d.total });
      addLog("success", `Iteration ${d.iteration}: ${d.passed}/${d.total} scenarios PASSED`);
    });

    es.addEventListener("certificate", (e) => {
      const d = JSON.parse(e.data);
      setCertificate(d);
      setPhase("verified");
      addLog("success", "=== MATHEMATICAL VERIFICATION COMPLETE ===");
      addLog("success", `Certificate: ${d.seal}`);
      es.close();
    });

    es.addEventListener("final_source", (e) => {
      const d = JSON.parse(e.data);
      setSourceCode(d.code);
    });

    es.addEventListener("failed", (e) => {
      setPhase("failed");
      addLog("error", "Verification loop exhausted max iterations.");
      es.close();
    });

    es.onerror = () => {
      es.close();
      if (phase !== "verified") {
        addLog("error", "SSE connection closed.");
      }
    };
  };

  const phaseColor = phase === "verified" ? "#4ade80" : phase === "variance" || phase === "failed" ? "#f87171" : phase === "prompting" ? "#a78bfa" : phase === "patching" ? "#fbbf24" : "#38bdf8";
  const phaseLabel = phase === "idle" ? "STANDBY" : phase === "running" ? "SIMULATING" : phase === "variance" ? "BUG FOUND" : phase === "prompting" ? "PROMPTING BOB 2.0" : phase === "patching" ? "APPLYING PATCH" : phase === "verified" ? "VERIFIED" : "FAILED";
  const progressPct = progress.total > 0 ? Math.round((progress.passed / progress.total) * 100) : 0;

  return (
    <div className="warroom-container">
      {/* ─── Top Status Bar ─── */}
      <div className="warroom-status-bar">
        <div className="warroom-status-left">
          <Shield className="h-5 w-5" style={{ color: phaseColor }} />
          <span className="warroom-phase" style={{ color: phaseColor }}>{phaseLabel}</span>
          {iteration > 0 && <span className="warroom-iter">ITERATION {iteration}</span>}
        </div>
        <div className="warroom-status-center">
          <div className="warroom-progress-track">
            <div className="warroom-progress-fill" style={{ width: `${progressPct}%`, background: phaseColor }} />
          </div>
          <span className="warroom-progress-label">{progress.passed}/{progress.total}</span>
        </div>
        <div className="warroom-status-right">
          <button className="warroom-btn warroom-btn-reset" onClick={() => void resetTarget()} disabled={phase === "running"}>
            <RefreshCw className="h-3.5 w-3.5" /> Reset
          </button>
          <select className="warroom-scenario-select" value={scenarioCount} onChange={e => setScenarioCount(Number(e.target.value))} disabled={phase === "running"}>
            <option value={100}>100 scenarios</option>
            <option value={500}>500 scenarios</option>
            <option value={1000}>1,000 scenarios</option>
            <option value={5000}>5,000 scenarios</option>
            <option value={10000}>10,000 scenarios</option>
          </select>
          <button className="warroom-btn warroom-btn-launch" onClick={startVerification} disabled={phase === "running" || phase === "prompting"}>
            {phase === "running" ? <Activity className="h-4 w-4 animate-pulse" /> : <Play className="h-4 w-4" />}
            {phase === "running" ? "Running..." : "Launch Matrix"}
          </button>
        </div>
      </div>

      {/* ─── Main Split View ─── */}
      <div className="warroom-split">
        {/* Left: Code Panel */}
        <div className="warroom-panel warroom-code-panel">
          <div className="warroom-panel-header">
            <Code2 className="h-4 w-4 text-[#a78bfa]" />
            <span>billing_engine.py</span>
            <span className="warroom-panel-tag">TARGET SERVICE</span>
          </div>
          <div className="warroom-code-body">
            <pre className="warroom-code-pre">
              {sourceCode.split("\n").map((line, i) => {
                const isChanged = changedLines.includes(i);
                return (
                  <div key={i} className={`warroom-code-line ${isChanged ? "warroom-code-line-changed" : ""}`}>
                    <span className="warroom-line-number">{i + 1}</span>
                    <span className="warroom-line-content">{line || " "}</span>
                  </div>
                );
              })}
            </pre>
          </div>
        </div>

        {/* Right: Matrix Terminal */}
        <div className="warroom-panel warroom-terminal-panel">
          <div className="warroom-panel-header">
            <Terminal className="h-4 w-4 text-[#4ade80]" />
            <span>Verification Matrix</span>
            <span className="warroom-panel-tag">LIVE FEED</span>
          </div>
          <div className="warroom-terminal-body" ref={logRef}>
            {logs.length === 0 && (
              <div className="warroom-terminal-empty">
                <Zap className="h-8 w-8 text-[#555]" />
                <p>Press <strong>Launch Matrix</strong> to start the adversarial verification loop.</p>
              </div>
            )}
            {logs.map(entry => (
              <div key={entry.id} className={`warroom-log warroom-log-${entry.type}`}>
                <span className="warroom-log-time">{entry.timestamp}</span>
                {entry.type === "error" && <AlertTriangle className="h-3.5 w-3.5 shrink-0" />}
                {entry.type === "success" && <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />}
                {entry.type === "ai" && <Zap className="h-3.5 w-3.5 shrink-0" />}
                <span className="warroom-log-msg">{entry.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Bottom: Variance Detail or Certificate ─── */}
      <div className="warroom-bottom">
        {variance && phase !== "verified" && (
          <div className="warroom-variance-card">
            <div className="warroom-variance-header">
              <AlertTriangle className="h-5 w-5 text-[#f87171]" />
              <span>VARIANCE DETECTED</span>
              <span className="warroom-variance-txid">{variance.failed_scenario.tx_id}</span>
            </div>
            <div className="warroom-variance-grid">
              {Object.entries(variance.variances).map(([key, val]) => (
                <div key={key} className="warroom-variance-item">
                  <div className="warroom-variance-key">{key.toUpperCase()}</div>
                  <div className="warroom-variance-expected">Expected: <strong>{val.expected}</strong></div>
                  <div className="warroom-variance-actual">Actual: <strong>{val.actual}</strong></div>
                </div>
              ))}
            </div>
          </div>
        )}
        {certificate && (
          <div className="warroom-certificate">
            <div className="warroom-cert-icon">
              <Shield className="h-10 w-10" />
            </div>
            <div className="warroom-cert-body">
              <div className="warroom-cert-title">MATHEMATICAL VERIFICATION CERTIFICATE</div>
              <div className="warroom-cert-detail">
                Code verified across <strong>{certificate.scenarios_passed}</strong> adversarial scenarios in <strong>{certificate.iterations}</strong> iteration(s).
              </div>
              <div className="warroom-cert-seal">{certificate.seal}</div>
            </div>
          </div>
        )}
        {phase === "idle" && (
          <div className="warroom-intro">
            <div className="warroom-intro-icon"><Zap className="h-8 w-8" /></div>
            <div>
              <div className="warroom-intro-title">Zero-Trust Verification Fabric</div>
              <div className="warroom-intro-detail">
                Load a target microservice. The Deterministic Oracle will blast it with thousands of adversarial synthetic transactions. If there is a single cent of variance, IBM Bob 2.0 will autonomously patch the code until the math is flawless.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
