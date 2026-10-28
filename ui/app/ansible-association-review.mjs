import React, { useState } from "react";

const e = React.createElement;
const DISPLAY_LIMIT = 80;

/**
 * Inventory mapping is a human assertion exported in a separate JSON document.
 * No workspace mutation/Engine actions, no automatic hostname/IP matching.
 */
export function AnsibleAssociationReview({ result, model, busy = false, onExport }) {
  const [choices, setChoices] = useState({});
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [exported, setExported] = useState(false);
  const preview = result.preview;
  const selected = Object.entries(choices)
    .filter(([, resourceId]) => resourceId !== "")
    .map(([ordinal, resourceId]) => ({ hostOrdinal: Number(ordinal), resourceId }))
    .sort((a, b) => a.hostOrdinal - b.hostOrdinal);
  const duplicateTargets = new Set(selected.map(x => x.resourceId)).size !== selected.length;
  const canExport = Boolean(model && model.resources.length && selected.length && !duplicateTargets &&
    acknowledged && !busy && !submitting && typeof onExport === "function");
  const submit = async () => {
    if (!canExport) return;
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
      setError(cause instanceof Error ? cause.message : "Inventory association export blocked.");
    } finally { setSubmitting(false); }
  };
  return e("section", { className: "network-import-preview",
    "data-ansible-association-review": model ? "REVIEW_REQUIRED" : "BUILDER_REQUIRED" },
    e("h3", null, "Associate declared inventory hosts with modeled resources (optional)"),
    e("p", { "data-ansible-association-boundary": "true", className: "helper-note" },
      "These are operator-selected, UNVERIFIED associations. Matching does not prove asset identity, IP allocation, reachability or physical topology. Export creates a separate JSON evidence report; Builder and Engine remain unchanged."),
    model
      ? e("p", { "data-ansible-model": "true" },
          `Builder: ${model.scenarioId} · source revision: ${model.sourceRevision} · resources: ${model.resources.length}`)
      : e("p", { "data-ansible-model-blocked": "true" },
          "Open a Builder scenario to associate inventory declarations. Read-only inspection is available in Runtime."),
    model && model.resources.length
      ? e("ol", { className: "validation-list", "data-ansible-association-hosts": "true" },
          ...preview.hosts.slice(0, DISPLAY_LIMIT).map((host, hostOrdinal) =>
            e("li", { key: `inventory-${hostOrdinal}` },
              e("label", null, `Declared ${host.inventoryName} (address: ${host.reportedConnectionAddress ?? "UNKNOWN"}) · `,
                e("select", {
                  "data-ansible-associate-host": String(hostOrdinal),
                  disabled: busy || submitting,
                  value: choices[hostOrdinal] ?? "",
                  onChange: event => {
                    setChoices(prev => ({ ...prev, [hostOrdinal]: event.target.value }));
                    setAcknowledged(false); setExported(false);
                  },
                },
                  e("option", { value: "" }, "Do not associate (default)"),
                  ...model.resources.map(resource =>
                    e("option", { key: resource.id, value: resource.id },
                      `${resource.label} [${resource.id}]`)))))))
      : null,
    preview.hosts.length > DISPLAY_LIMIT
      ? e("p", { "data-ansible-association-limit": "true" },
          `Only first ${DISPLAY_LIMIT} of ${preview.hosts.length} inventory hosts can be reviewed; the remainder stay unassociated.`)
      : null,
    duplicateTargets
      ? e("p", { role: "alert", "data-ansible-association-conflict": "BLOCKED" },
          "Two inventory hosts cannot be assigned to the same modeled resource in this strict review profile.")
      : null,
    e("p", null, `Explicit host associations: ${selected.length}. Unselected hosts remain unassociated.`),
    e("label", null,
      e("input", { type: "checkbox", "data-ansible-association-ack": "true",
        checked: acknowledged, disabled: busy || submitting || !model || !selected.length || duplicateTargets,
        onChange: event => { setAcknowledged(event.target.checked); setExported(false); } }),
      " I acknowledge these are my unverified inventory-to-model associations, not independently verified asset identities."),
    e("button", { type: "button", "data-ansible-association-export": "true",
      disabled: !canExport, onClick: () => { void submit(); } },
      submitting ? "Validating association…" : "Export reviewed associations (JSON)"),
    error ? e("p", { role: "alert", "data-ansible-association-error": "BLOCKED" }, error) : null,
    exported ? e("p", { "data-ansible-association-exported": "true" },
      "Association sidecar exported. No Builder scenario or Engine state was modified.") : null);
}
