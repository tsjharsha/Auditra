import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { useMemo, useState } from "react";
import { jsonPreview, shortId } from "../../lib/format";
import type { EvidenceGraph, RelationshipModel } from "../../types/auditra";
import { Card, SectionHeader } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/State";

const nodeColors: Record<string, string> = {
  MERCHANT: "#111827",
  ORDER: "#4338ca",
  PAYMENT: "#0f766e",
  SETTLEMENT: "#b45309",
  REFUND: "#be123c",
  FEE_RULE: "#334155",
};

export function SchemaRelationshipFlow({ model }: { model?: RelationshipModel | null }) {
  const graph = useMemo(() => {
    if (!model) return { nodes: [], edges: [] };
    const positions: Record<string, { x: number; y: number }> = {
      MERCHANT: { x: 80, y: 120 },
      ORDER: { x: 280, y: 120 },
      PAYMENT: { x: 500, y: 120 },
      SETTLEMENT: { x: 740, y: 20 },
      REFUND: { x: 740, y: 130 },
      FEE_RULE: { x: 740, y: 240 },
    };
    const nodes: Node[] = model.nodes.map((node, index) => ({
      id: node,
      position: positions[node] ?? { x: 120 + index * 170, y: 120 },
      data: { label: node.replace("_", " ") },
      style: {
        border: `1px solid ${nodeColors[node] ?? "#d8dee8"}`,
        background: "#fff",
        borderRadius: 8,
        color: nodeColors[node] ?? "#111827",
        fontWeight: 800,
        padding: 12,
        width: 140,
      },
    }));
    const edges: Edge[] = model.edges.map((edge, index) => ({
      id: `${edge.source}-${edge.target}-${index}`,
      source: edge.source,
      target: edge.target,
      label: edge.relationship,
      animated: edge.required,
      style: { stroke: edge.required ? "#0f766e" : "#98a2b3" },
      data: { ...edge },
    }));
    return { nodes, edges };
  }, [model]);

  if (!model) return <EmptyState title="No relationship model" detail="Preview or build a world to see the financial structure." />;

  return (
    <Card className="p-0">
      <div className="h-[390px] overflow-hidden rounded-lg">
        <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView minZoom={0.5}>
          <Background color="#d8dee8" gap={18} />
          <MiniMap pannable zoomable />
          <Controls />
        </ReactFlow>
      </div>
    </Card>
  );
}

export function CaseEvidenceFlow({ graph }: { graph?: EvidenceGraph | null }) {
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const reactFlowGraph = useMemo(() => toReactFlow(graph), [graph]);

  if (!graph || !graph.nodes.length) {
    return <EmptyState title="No graph selected" detail="Open an audited case to inspect its financial evidence graph." />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <Card className="p-0">
        <div className="h-[560px] overflow-hidden rounded-lg">
          <ReactFlow
            nodes={reactFlowGraph.nodes}
            edges={reactFlowGraph.edges}
            fitView
            minZoom={0.35}
            onNodeClick={(_, node) => setSelected({ kind: "node", ...node.data })}
            onEdgeClick={(_, edge) => setSelected({ kind: "edge", ...edge.data })}
          >
            <Background color="#d8dee8" gap={18} />
            <MiniMap pannable zoomable />
            <Controls />
          </ReactFlow>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Selection" kicker={`${graph.nodes.length} nodes / ${graph.edges.length} edges`} />
        <pre className="max-h-[470px] overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
          {selected ? jsonPreview(selected, 2000) : "Select a node or edge"}
        </pre>
      </Card>
    </div>
  );
}

function toReactFlow(graph?: EvidenceGraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!graph) return { nodes: [], edges: [] };
  const center = { x: 440, y: 260 };
  const radius = Math.max(180, Math.min(320, graph.nodes.length * 16));
  const nodes: Node[] = graph.nodes.map((node, index) => {
    const isCenter = index === 0 || node.id.includes("TRANSACTION");
    const angle = (Math.PI * 2 * Math.max(index - 1, 0)) / Math.max(1, graph.nodes.length - 1);
    const position = isCenter
      ? center
      : {
          x: center.x + Math.cos(angle) * radius,
          y: center.y + Math.sin(angle) * radius,
        };
    const color = colorForType(node.type);
    return {
      id: node.id,
      position,
      data: { ...node, label: shortId(node.label || node.id, 20) },
      style: {
        border: `1px solid ${color}`,
        background: "#fff",
        borderRadius: 8,
        color,
        fontWeight: 800,
        minWidth: 130,
      },
    };
  });
  const edges: Edge[] = graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.relationship,
    animated: edge.relationship === "CONTRADICTED_BY",
    style: { stroke: edge.relationship === "CONTRADICTED_BY" ? "#be123c" : "#64748b" },
    data: { ...edge },
  }));
  return { nodes, edges };
}

function colorForType(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes("payment") || normalized.includes("transaction")) return "#0f766e";
  if (normalized.includes("settlement")) return "#b45309";
  if (normalized.includes("refund")) return "#be123c";
  if (normalized.includes("decision")) return "#4338ca";
  if (normalized.includes("evidence")) return "#334155";
  return "#111827";
}
