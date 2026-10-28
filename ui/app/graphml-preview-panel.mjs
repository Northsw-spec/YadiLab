import React, { useEffect, useRef, useState } from "react";

const e = React.createElement;
const MAX_VISIBLE_ROWS = 80;

/**
 * Pure display projection. JSX-like React elements escape all imported labels;
 * there is deliberately no HTML injection, scenario/Engine activation control
 * or claim that GraphML relations are confirmed physical links.
 */
export function GraphmlPreviewDetails({ result }) {
  if (!result) return e("p", { "data-graphml-empty": "true" }, "Choose a GraphML file for read-only inspection.");
  const { preview, filename } = result;
  const displayedNodes = preview.nodes.slice(0, MAX_VISIBLE_ROWS);
  const displayedEdges = preview.edges.slice(0, MAX_VISIBLE_ROWS);
  return e("section", { className: "network-import-preview", "data-graphml-preview": "REVIEW_REQUIRED" },
    e("h3", null, "GraphML preview — ", filename),
    e("p", { "data-graphml-summary": "true" }, `Graph: ${preview.graphId} · Nodes: ${preview.nodes.length} · Graph edges: ${preview.edges.length}`),
    e("p", { "data-graphml-source-hash": "true" }, `SHA-256: ${preview.sourceSha256}`),
    e("p", { className: "helper-note", "data-graphml-truth-boundary": "true" },
      "GRAPH_EDGE means a relationship drawn or declared in a graph, NOT a confirmed physical cable. No node type, OS, IP address, reachability, routing or Engine PASS is inferred. Active workspace remains unchanged."),
    e("h4", null, "Declared nodes (read-only)"),
    e("ul", { className: "validation-list", "data-graphml-nodes": "true" },
      ...displayedNodes.map((n, i) => e("li", { key: `${n.id}-${i}` }, n.label === undefined ? n.id : `${n.id} — ${n.label}`))),
    preview.nodes.length > MAX_VISIBLE_ROWS ? e("p", null, `Showing first ${MAX_VISIBLE_ROWS} of ${preview.nodes.length} nodes.`) : null,
    e("h4", null, "Graph edges (not verified cables)"),
    e("ul", { className: "validation-list", "data-graphml-edges": "true" },
      ...displayedEdges.map((edge, i) => e("li", { key: `${edge.id ?? "edge"}-${i}` },
        `${edge.id ?? `edge ${i + 1}`}: ${edge.sourceId} → ${edge.targetId} (${edge.directed ? "directed" : "undirected"}; GRAPH_EDGE)`))),
    preview.edges.length > MAX_VISIBLE_ROWS ? e("p", null, `Showing first ${MAX_VISIBLE_ROWS} of ${preview.edges.length} edges.`) : null,
    preview.diagnostics.length
      ? e("ul", { className: "validation-list", "data-graphml-warnings": "true" },
          ...preview.diagnostics.map((d, i) => e("li", { key: i }, `${d.code}: ${d.message}`)))
      : null,
    e("p", { className: "helper-note", "data-graphml-activation-status": "BLOCKED" },
      "Preview only. GraphML-to-Builder mapping and topology activation are NOT enabled in this checkpoint."),
  );
}

/** Isolated dialog. It never receives setWorkspace or an activation callback. */
export function GraphmlReadOnlyPanel({ onClose, inspectFile }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useRef(0);
  const panel = useRef(null);

  useEffect(() => {
    panel.current?.focus();
    return () => { request.current++; };
  }, []);
  useEffect(() => {
    const escape = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [busy, onClose]);

  const chooseFile = async (file) => {
    if (!file || busy) return;
    const id = ++request.current;
    setResult(null);
    setError("");
    setBusy(true);
    try {
      const parsed = await inspectFile(file);
      if (request.current === id) setResult(parsed);
    } catch (cause) {
      if (request.current === id) setError(cause?.code ? `${cause.code}: ${cause.message}` : cause instanceof Error ? cause.message : String(cause));
    } finally {
      if (request.current === id) setBusy(false);
    }
  };

  return e("div", { className: "network-import-overlay", "data-graphml-overlay": "true" },
    e("section", { className: "network-import-panel", ref: panel, tabIndex: -1, role: "dialog",
      "aria-modal": "true", "aria-label": "GraphML read-only preview", "data-graphml-panel": "PREVIEW_ONLY" },
      e("div", { className: "network-import-heading" },
        e("div", null, e("h2", null, "Inspect GraphML — preview only"),
          e("p", null, "Offline structural inspection. No graph relation is activated as a network link.")),
        e("button", { type: "button", onClick: () => { request.current++; onClose(); }, disabled: busy, "aria-label": "Close GraphML preview" }, "Close")),
      e("label", { className: "file-button" }, busy ? "Reading GraphML…" : "Choose .graphml file",
        e("input", { type: "file", accept: ".graphml", disabled: busy, "data-graphml-file": "true",
          onChange: (event) => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (file) void chooseFile(file);
          }, hidden: true })),
      error ? e("p", { role: "alert", className: "helper-status blocked", "data-graphml-error": "BLOCKED" }, error) : null,
      e(GraphmlPreviewDetails, { result }),
      e("div", { className: "network-import-actions" },
        e("button", { type: "button", disabled: busy, "data-graphml-cancel": "true",
          onClick: () => { request.current++; onClose(); } }, "Close without changes")),
    ),
  );
}
