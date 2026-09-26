import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, Shield, Terminal, Zap, ShieldAlert, Cpu, Database, Server, RefreshCw, Code2, AlertTriangle, CheckCircle } from "lucide-react";

const API_BASE = import.meta.env.VITE_AUDITRA_API_BASE ?? "http://127.0.0.1:8002";

type NodeStatus = 
  | "IDLE" 
  | "ATTACKING" 
  | "COMPROMISED" 
  | "ANALYZING" 
  | "PATCHING" 
  | "VALIDATING" 
  | "REVERIFYING" 
  | "SECURED" 
  | "PATCH_FAILED" 
  | "VERIFICATION_FAILED" 
  | "ROLLING_BACK" 
  | "ROLLED_BACK";

interface NodeState {
  id: string;
  name: string;
  status: NodeStatus;
  icon: any;
  variance?: any;
  error?: string;
  metrics?: { passed?: number; failed?: number; total_tests?: number; oracle_agreement?: string };
}

interface LogEntry {
  id: number;
  timestamp: string;
  type: "info" | "error" | "success" | "ai" | "warning";
  message: string;
}

export function WarRoomPage() {
  const [phase, setPhase] = useState<"idle" | "running" | "verified" | "failed">("idle");
  const [mode, setMode] = useState<string>("STANDBY");
  const [nodes, setNodes] = useState<Record<string, NodeState>>({
    tax_router: { id: "tax_router", name: "Tax Router", status: "IDLE", icon: Server },
    billing_engine: { id: "billing_engine", name: "Billing Engine", status: "IDLE", icon: Database },
    ledger_sync: { id: "ledger_sync", name: "Ledger Sync", status: "IDLE", icon: Activity },
    fraud_detector: { id: "fraud_detector", name: "Fraud Detector", status: "IDLE", icon: ShieldAlert },
  });
  
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [activeCode, setActiveCode] = useState<string>("WAITING FOR AST PATCH...");
  const [auditId, setAuditId] = useState<string | null>(null);
  
  const logRef = useRef<HTMLDivElement>(null);
  const logIdRef = useRef(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  const now = () => new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const addLog = useCallback((type: LogEntry["type"], message: string) => {
    const entry: LogEntry = { id: logIdRef.current++, timestamp: now(), type, message };
    setLogs(prev => [...prev, entry]);
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const updateNode = (id: string, status: NodeStatus, extra: any = {}) => {
    setNodes(prev => {
      if (!prev[id]) return prev;
      return {
        ...prev,
        [id]: { ...prev[id], status, ...extra }
      };
    });
  };

  const resetGrid = async () => {
    await fetch(`${API_BASE}/verification/reset`, { method: "POST" });
    setPhase("idle");
    setMode("STANDBY");
    setLogs([]);
    setActiveCode("SYSTEM STANDBY...");
    setNodes(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(k => { 
        next[k] = { ...next[k], status: "IDLE", variance: undefined, error: undefined, metrics: undefined };
      });
      return next;
    });
    addLog("info", "All nodes restored to known-vulnerable states from templates.");
  };

  const startAegis = () => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    setPhase("running");
    setLogs([]);
    setActiveCode("INITIALIZING AEGIS DEFENSE GRID...");
    
    setNodes(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(k => { next[k] = { ...next[k], status: "IDLE", variance: undefined, error: undefined, metrics: undefined }; });
      return next;
    });

    const es = new EventSource(`${API_BASE}/verification/stream`);
    eventSourceRef.current = es;

    es.addEventListener("aegis_start", (e) => {
      const d = JSON.parse(e.data);
      if (d.audit_id) setAuditId(d.audit_id);
      setMode(d.message.includes("LIVE") ? "LIVE AI (GROQ LLAMA-3)" : "DETERMINISTIC DEMO");
      addLog("info", d.message);
    });

    es.addEventListener("node_state", (e) => {
      const d = JSON.parse(e.data);
      updateNode(d.node, d.state, d);
      
      const nodeName = d.node.toUpperCase();
      
      switch (d.state) {
        case "MUTATING":
          addLog("warning", `[MUTATION_ENGINE] ${d.message}`);
          break;
        case "MUTATION_DETECTED":
          addLog("success", `[MUTATION_ENGINE] ${d.message}`);
          break;
        case "MUTATION_FAILED":
          addLog("error", `[MUTATION_ENGINE] ${d.message}`);
          break;
        case "ATTACKING":
          addLog("info", `[${nodeName}] Running adversarial testing sandbox...`);
          break;
        case "COMPROMISED":
          addLog("error", `[${nodeName}] ORACLE MISMATCH DETECTED. Node compromised.`);
          if (d.variance?.variances) {
             Object.keys(d.variance.variances).forEach(k => {
                addLog("error", `  ${k} -> expected: ${d.variance.variances[k].expected} | actual: ${d.variance.variances[k].actual}`);
             });
          }
          break;
        case "ANALYZING":
          addLog("ai", `[${nodeName}] Extracting failure fingerprint...`);
          break;
        case "PATCHING":
          addLog("ai", `[${nodeName}] Requesting repair proposal from IBM Bob 2.0 / LLM...`);
          break;
        case "VALIDATING":
          if (d.patch_code) setActiveCode(d.patch_code);
          addLog("warning", `[${nodeName}] Patch received. Running AST syntax and security validation...`);
          if (d.patch_impact) {
            addLog("info", `  -> Patch impact: +${d.patch_impact.added} lines / -${d.patch_impact.removed} lines`);
          }
          break;
        case "REVERIFYING":
          addLog("info", `[${nodeName}] Patch safely applied to sandbox. Post-patch adversarial re-verification running (${d.metrics?.total_tests || 20} tests)...`);
          break;
        case "SECURED":
          addLog("success", `[${nodeName}] POST-PATCH VERIFICATION PASSED. Tests: ${d.metrics?.passed}/${d.metrics?.passed} | Oracle: ${d.metrics?.oracle_agreement}. Node is SECURE.`);
          break;
        case "VERIFICATION_FAILED":
          addLog("error", `[${nodeName}] POST-PATCH VERIFICATION FAILED. Tests: ${d.metrics?.passed || 0}/${d.metrics?.total || 0} passed.`);
          if (d.rejection_reason) {
            addLog("error", `  -> WHY REJECTED: ${d.rejection_reason}`);
          }
          break;
        case "PATCH_FAILED":
          addLog("error", `[${nodeName}] SECURITY EXCEPTION: LLM generated invalid or dangerous AST: ${d.error}`);
          break;
        case "ROLLING_BACK":
          addLog("warning", `[${nodeName}] Patch rejected. Initiating secure rollback to last known state...`);
          break;
        case "ROLLED_BACK":
          addLog("error", `[${nodeName}] ROLLBACK COMPLETE. Node remains isolated.`);
          break;
      }
    });

    es.addEventListener("aegis_secure", (e) => {
      const d = JSON.parse(e.data);
      setPhase("verified");
      addLog("success", `=== ${d.message} | RELEASE STATUS: ${d.release_status} ===`);
      es.close();
    });

    es.addEventListener("aegis_blocked", (e) => {
      const d = JSON.parse(e.data);
      setPhase("failed");
      addLog("error", `=== ${d.message} | RELEASE STATUS: ${d.release_status} ===`);
      es.close();
    });

    es.onerror = () => {
      es.close();
    };
  };

  const getStatusColor = (status: NodeStatus) => {
    if (["IDLE"].includes(status)) return "#334155";
    if (["ATTACKING", "ANALYZING"].includes(status)) return "#38bdf8";
    if (["PATCHING", "VALIDATING", "REVERIFYING"].includes(status)) return "#a855f7";
    if (["COMPROMISED", "VERIFICATION_FAILED", "PATCH_FAILED", "ROLLING_BACK", "ROLLED_BACK"].includes(status)) return "#ef4444";
    if (["SECURED"].includes(status)) return "#4ade80";
    return "#334155";
  };

  return (
    <div className="warroom-container">
      {/* ─── Top Status Bar ─── */}
      <div className="warroom-status-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Shield className="h-5 w-5 text-indigo-400" />
          <span style={{ fontWeight: 800, letterSpacing: '0.1em', fontSize: '1.125rem' }}>AUDITRA: AEGIS PROTOCOL</span>
          <span style={{ marginLeft: '1rem', padding: '0.25rem 0.75rem', background: 'rgba(255,255,255,0.1)', borderRadius: '999px', fontSize: '0.75rem' }}>
            MODE: {mode}
          </span>
          {auditId && (
            <span style={{ marginLeft: '0.5rem', padding: '0.25rem 0.75rem', background: 'rgba(168,85,247,0.2)', color: '#d8b4fe', borderRadius: '999px', fontSize: '0.75rem', fontFamily: 'monospace' }}>
              ID: {auditId}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="warroom-btn warroom-btn-reset" onClick={resetGrid} disabled={phase === "running"}>
            <RefreshCw className="h-4 w-4" /> Reset Environment
          </button>
          <button className="warroom-btn warroom-btn-launch" onClick={startAegis} disabled={phase === "running"}>
            <Zap className="h-4 w-4" /> Launch Verification Grid
          </button>
        </div>
      </div>

      {/* ─── 4 Blocks (Nodes) ─── */}
      <div className="aegis-node-grid">
        {Object.values(nodes).map(node => {
          const color = getStatusColor(node.status);
          return (
            <div key={node.id} className="aegis-node" style={{ borderColor: color, boxShadow: node.status !== 'IDLE' ? `0 0 10px ${color}33` : 'none' }}>
              <div className="aegis-node-header">
                <node.icon className="h-5 w-5" style={{ color }} />
                <span>{node.name}</span>
                <div className="aegis-node-badge" style={{ color }}>{node.status}</div>
              </div>
              <div className="aegis-node-body">
                {node.status === "COMPROMISED" && node.variance && (
                  <div className="aegis-alert" style={{ color: '#ef4444' }}>
                    <AlertTriangle className="h-3 w-3" />
                    <span>ORACLE MISMATCH DETECTED</span>
                  </div>
                )}
                {["PATCHING", "VALIDATING", "REVERIFYING"].includes(node.status) && (
                  <div className="aegis-alert" style={{ color: '#a855f7' }}>
                    <Cpu className="h-3 w-3 animate-pulse" />
                    <span>{node.status === 'VALIDATING' ? 'AST VALIDATION...' : node.status === 'REVERIFYING' ? 'POST-PATCH SANDBOX EXECUTION...' : 'AI PROPOSING REPAIR...'}</span>
                  </div>
                )}
                {node.status === "SECURED" && (
                  <div className="aegis-alert" style={{ color: '#4ade80' }}>
                    <Shield className="h-3 w-3" />
                    <span>VERIFICATION PASSED</span>
                  </div>
                )}
                {["ROLLED_BACK"].includes(node.status) && (
                  <div className="aegis-alert" style={{ color: '#ef4444' }}>
                    <AlertTriangle className="h-3 w-3" />
                    <span>PATCH REJECTED. ROLLED BACK.</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ─── 2 Editors ─── */}
      <div className="warroom-layout">
        <div className="warroom-pane">
          <div className="warroom-pane-header">
            <Code2 className="h-4 w-4" />
            <span>Untrusted AI Patch Proposal</span>
          </div>
          <pre className="warroom-code-viewer">
            <code>{activeCode}</code>
          </pre>
        </div>

        <div className="warroom-pane">
          <div className="warroom-pane-header">
            <Terminal className="h-4 w-4" />
            <span>Verification Engine STDOUT</span>
            {phase === "verified" && (
              <span style={{ marginLeft: "auto", color: "#4ade80", fontWeight: "bold", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                <CheckCircle className="h-4 w-4" /> PRODUCTION GATE: READY
              </span>
            )}
            {phase === "failed" && (
              <span style={{ marginLeft: "auto", color: "#ef4444", fontWeight: "bold", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                <ShieldAlert className="h-4 w-4" /> PRODUCTION GATE: BLOCKED
              </span>
            )}
          </div>
          <div className="warroom-console-logs" ref={logRef}>
            {logs.map(entry => (
              <div key={entry.id} className={`warroom-log warroom-log-${entry.type}`}>
                <span className="warroom-log-time">[{entry.timestamp}]</span>
                <span className="warroom-log-msg">{entry.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
