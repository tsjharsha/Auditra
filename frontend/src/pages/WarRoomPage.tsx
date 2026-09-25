import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, Shield, Terminal, Zap, ShieldAlert, Cpu, Database, Server, RefreshCw, Code2 } from "lucide-react";

const API_BASE = import.meta.env.VITE_AUDITRA_API_BASE ?? "http://127.0.0.1:8002";

type NodeStatus = "IDLE" | "ATTACKED" | "COMPROMISED" | "PATCHING" | "SECURE";

interface NodeState {
  id: string;
  name: string;
  status: NodeStatus;
  icon: any;
  variance?: any;
}

interface LogEntry {
  id: number;
  timestamp: string;
  type: "info" | "error" | "success" | "ai";
  message: string;
}

export function WarRoomPage() {
  const [phase, setPhase] = useState<"idle" | "running" | "verified">("idle");
  const [nodes, setNodes] = useState<Record<string, NodeState>>({
    tax_router: { id: "tax_router", name: "Tax Router", status: "IDLE", icon: Server },
    billing_engine: { id: "billing_engine", name: "Billing Engine", status: "IDLE", icon: Database },
    ledger_sync: { id: "ledger_sync", name: "Ledger Sync", status: "IDLE", icon: Activity },
    fraud_detector: { id: "fraud_detector", name: "Fraud Detector", status: "IDLE", icon: ShieldAlert },
  });
  
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [activeCode, setActiveCode] = useState<string>("SYSTEM STANDBY...");
  
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
    setNodes(prev => ({
      ...prev,
      [id]: { ...prev[id], status, ...extra }
    }));
  };

  const resetGrid = async () => {
    await fetch(`${API_BASE}/verification/reset`, { method: "POST" });
    setPhase("idle");
    setLogs([]);
    setActiveCode("SYSTEM STANDBY...");
    setNodes(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(k => { next[k].status = "IDLE"; next[k].variance = undefined; });
      return next;
    });
  };

  const startAegis = () => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    setPhase("running");
    setLogs([]);
    setActiveCode("INITIALIZING AEGIS DEFENSE GRID...");
    
    setNodes(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(k => { next[k].status = "IDLE"; next[k].variance = undefined; });
      return next;
    });

    const es = new EventSource(`${API_BASE}/verification/stream`);
    eventSourceRef.current = es;

    es.addEventListener("aegis_start", (e) => {
      const d = JSON.parse(e.data);
      addLog("info", d.message);
    });

    es.addEventListener("node_attacked", (e) => {
      const d = JSON.parse(e.data);
      updateNode(d.node, "ATTACKED");
      addLog("info", `[${d.node.toUpperCase()}] INCOMING PULL REQUEST DETECTED...`);
    });

    es.addEventListener("variance_detected", (e) => {
      const d = JSON.parse(e.data);
      updateNode(d.node, "COMPROMISED", { variance: d });
      addLog("error", `[${d.node.toUpperCase()}] CRYPTOGRAPHIC DRIFT DETECTED IN AST.`);
      Object.keys(d.variances).forEach(k => {
        addLog("error", `  ${k} -> EXPECTED: ${d.variances[k].expected} | ACTUAL: ${d.variances[k].actual}`);
      });
      addLog("error", `  ORACLE HASH: ${d.oracle_hash}`);
      addLog("error", `  TARGET HASH: ${d.target_hash}`);
    });

    es.addEventListener("prompting_ai", (e) => {
      const d = JSON.parse(e.data);
      updateNode(d.node, "PATCHING");
      addLog("ai", `[${d.node.toUpperCase()}] REQUESTING IBM BOB 2.0 ZERO-TRUST PATCH...`);
    });

    es.addEventListener("patch_applied", (e) => {
      const d = JSON.parse(e.data);
      setActiveCode(d.code);
      addLog("success", `[${d.node.toUpperCase()}] PATCH APPLIED TO DISK. HOT-RELOADING NODE...`);
    });

    es.addEventListener("node_secured", (e) => {
      const d = JSON.parse(e.data);
      updateNode(d.node, "SECURE");
      addLog("success", `[${d.node.toUpperCase()}] MATHEMATICAL VERIFICATION COMPLETE. NODE SECURED.`);
    });

    es.addEventListener("aegis_secure", (e) => {
      setPhase("verified");
      addLog("success", "=== ALL NODES SECURED. AEGIS GRID IS ONLINE. ===");
      es.close();
    });

    es.onerror = () => {
      es.close();
    };
  };

  return (
    <div className="warroom-container">
      {/* ─── Top Status Bar ─── */}
      <div className="warroom-status-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Shield className="h-5 w-5 text-indigo-400" />
          <span style={{ fontWeight: 800, letterSpacing: '0.1em', fontSize: '1.125rem' }}>AEGIS PROTOCOL</span>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="warroom-btn warroom-btn-reset" onClick={resetGrid} disabled={phase === "running"}>
            <RefreshCw className="h-4 w-4" /> Reset
          </button>
          <button className="warroom-btn warroom-btn-launch" onClick={startAegis} disabled={phase === "running"}>
            <Zap className="h-4 w-4" /> Launch Grid
          </button>
        </div>
      </div>

      {/* ─── 4 Blocks (Nodes) ─── */}
      <div className="aegis-node-grid">
        {Object.values(nodes).map(node => (
          <div key={node.id} className={`aegis-node node-status-${node.status}`}>
            <div className="aegis-node-header">
              <node.icon className="h-5 w-5" />
              <span>{node.name}</span>
              <div className="aegis-node-badge">{node.status}</div>
            </div>
            <div className="aegis-node-body">
              {node.status === "COMPROMISED" && node.variance && (
                <div className="aegis-alert text-red-400">
                  <span>DRIFT: {node.variance.target_hash}</span>
                </div>
              )}
              {node.status === "PATCHING" && (
                <div className="aegis-alert text-purple-400">
                  <Cpu className="h-3 w-3 animate-pulse" />
                  <span>GENERATING AST PATCH...</span>
                </div>
              )}
              {node.status === "SECURE" && (
                <div className="aegis-alert text-green-400">
                  <Shield className="h-3 w-3" />
                  <span>CRYPTOGRAPHICALLY SEALED</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ─── 2 Editors ─── */}
      <div className="warroom-layout">
        {/* Editor 1: AST Patch Viewer */}
        <div className="warroom-pane">
          <div className="warroom-pane-header">
            <Code2 className="h-4 w-4" />
            <span>AST Patch Viewer</span>
          </div>
          <pre className="warroom-code-viewer">
            <code>{activeCode}</code>
          </pre>
        </div>

        {/* Editor 2: Console */}
        <div className="warroom-pane">
          <div className="warroom-pane-header">
            <Terminal className="h-4 w-4" />
            <span>System STDOUT</span>
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
