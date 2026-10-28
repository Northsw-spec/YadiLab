import React, { useState } from "react";

const e = React.createElement;
const DISPLAY_LIMIT = 80;

/**
 * Read-only source-to-resource association review.
 * This panel does NOT modify Builder, Engine or observed scan records.
 * The optional export callback can only create an independent evidence file.
 */
export function NmapAssociationReview({ result, model, busy = false, onExport }) {
  const [choices, setChoices] = useState({});
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [exported, setExported] = useState(false);
  const preview = result.preview;
  const selected = Object.entries(choices)
    .filter(([, resourceId]) => resourceId !== "")
    .map(([hostOrdinal, resourceId]) => ({ hostOrdinal: Number(hostOrdinal), resourceId }))
    .sort((a, b) => a.hostOrdinal - b.hostOrdinal);
  const duplicates = new Set(selected.map((x) => x.resourceId)).size !== selected.length;
  const enabled = Boolean(model && model.resources.length && selected.length && !duplicates && acknowledged &&
    !busy && !submitting && typeof onExport === "function");
  const submit = async () => {
    if (!enabled) return;
    setSubmitting(true); setError(""); setExported(false);
    try {
      await onExport(preview, {
        sourceSha256: preview.sourceSha256,
        scenarioId: model.scenarioId,
        sourceRevision: model.sourceRevision,
        associations: selected,
        acknowledgeNotVerified: acknowledged,
      });
      setExported(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Evidence association export blocked.");
    } finally {
      setSubmitting(false);
    }
  };
  return e("section", { className: "network-import-preview", "data-nmap-association-review": model ? "REVIEW_REQUIRED" : "BUILDER_REQUIRED" },
    e("h3", null, "Associate observations with modeled resources (optional)"),
    e("p", { className: "helper-note", "data-nmap-association-boundary": "true" },
      "An association is a human-selected reference, NOT proof that the scan host and modeled resource are identical. No IP, hostname, port, network link, reachability or Engine status is modified. Export is a separate JSON evidence document."),
    model
      ? e("p", { "data-nmap-model": "true" }, `Builder: ${model.scenarioId} · source revision: ${model.sourceRevision} · available resources: ${model.resources.length}`)
      : e("p", { "data-nmap-model-blocked": "true" }, "Open an existing Builder scenario to associate observations; inspection remains available in Runtime."),
    model && model.resources.length
      ? e("ol", { className: "validation-list", "data-nmap-association-hosts": "true" },
          ...preview.hosts.slice(0, DISPLAY_LIMIT).map((host, hostOrdinal) =>
            e("li", { key: `host-${hostOrdinal}` },
              e("label", null,
                `Observed ${host.ipv4} (scan status ${host.observedStatus}) · `,
                e("select", {
                  "data-nmap-associate-host": String(hostOrdinal),
                  disabled: busy || submitting, value: choices[hostOrdinal] ?? "",
                  onChange: (event) => {
                    const value = event.target.value;
                    setChoices((prev) => ({ ...prev, [hostOrdinal]: value }));
                    setAcknowledged(false); setExported(false);
                  },
                },
                  e("option", { value: "" }, "Do not associate (default)"),
                  ...model.resources.map((resource) =>
                    e("option", { key: resource.id, value: resource.id },
                      `${resource.label} [${resource.id}]`)))))))
      : null,
    preview.hosts.length > DISPLAY_LIMIT
      ? e("p", { "data-nmap-association-limit": "true" },
          `Only the first ${DISPLAY_LIMIT} of ${preview.hosts.length} observations may be reviewed here. Unshown records remain unassociated.`)
      : null,
    duplicates ? e("p", { role: "alert", "data-nmap-association-conflict": "BLOCKED" },
      "Two observed hosts cannot be associated with the same modeled resource in this strict profile.") : null,
    e("p", null, `Explicit host associations: ${selected.length}. Unselected observations remain unassociated.`),
    e("label", null,
      e("input", { type: "checkbox", checked: acknowledged, disabled: busy || submitting || !model || !selected.length || duplicates,
        "data-nmap-association-ack": "true",
        onChange: (ev) => { setAcknowledged(ev.target.checked); setExported(false); } }),
      " I acknowledge these are my own unverified associations, not independently verified asset identities."),
    e("button", { type: "button", "data-nmap-association-export": "true",
      disabled: !enabled, onClick: () => { void submit(); } },
      submitting ? "Validating evidence…" : "Export reviewed associations (JSON)"),
    error ? e("p", { role: "alert", "data-nmap-association-error": "BLOCKED" }, error) : null,
    exported ? e("p", { "data-nmap-association-exported": "true" },
      "Association sidecar exported. No YadiLab scenario, Builder resources, links or Engine state were modified.") : null,
  );
}
