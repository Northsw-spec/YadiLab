import React, { useState } from "react";
const e = React.createElement;
const DISPLAY_LIMIT = 80;

/** Explicit human-reviewed INI declarations, never verified physical topology. */
export function AnsibleIniAssociationReview({ result, model, busy = false, onExportAssociation }) {
  const [choices, setChoices] = useState({});
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [exported, setExported] = useState(false);
  const preview = result.preview;
  const selected = Object.entries(choices)
    .filter(([, resourceId]) => resourceId !== "")
    .map(([ordinal, resourceId]) => ({ hostOrdinal: Number(ordinal), resourceId }))
    .sort((a,b) => a.hostOrdinal - b.hostOrdinal);
  const duplicateTargets = new Set(selected.map(x => x.resourceId)).size !== selected.length;
  const canExport = Boolean(model && model.resources.length && selected.length && !duplicateTargets &&
    acknowledged && !busy && !submitting && typeof onExportAssociation === "function");
  const submit = async () => {
    if (!canExport) return;
    setSubmitting(true); setError(""); setExported(false);
    try {
      await onExportAssociation(preview, {
        sourceSha256: preview.sourceSha256,
        scenarioId: model.scenarioId,
        sourceRevision: model.sourceRevision,
        associations: selected,
        acknowledgeNotVerified: acknowledged,
      });
      setExported(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ansible INI association export blocked.");
    } finally { setSubmitting(false); }
  };
  return e("section", { className: "network-import-preview",
      "data-ansible-ini-association-review": model ? "REVIEW_REQUIRED" : "BUILDER_REQUIRED" },
    e("h3", null, "Review associations to already modeled Builder resources (optional)"),
    e("p", { className: "helper-note", "data-ansible-ini-association-boundary": "true" },
      "Associations are operator-selected, UNVERIFIED references. They do not prove asset identity, current IP assignment, physical cable, reachability or Engine PASS. A separate JSON sidecar is downloaded; Builder and Engine stay unchanged."),
    model
      ? e("p", { "data-ansible-ini-model": "true" },
          `Builder: ${model.scenarioId} · source revision: ${model.sourceRevision} · resources: ${model.resources.length}`)
      : e("p", { "data-ansible-ini-model-blocked": "true" },
          "Open an existing Builder scenario to associate inventory declarations. Runtime inspection remains read-only."),
    model && model.resources.length
      ? e("ol", { className: "validation-list", "data-ansible-ini-association-hosts": "true" },
          ...preview.hosts.slice(0, DISPLAY_LIMIT).map((host, hostOrdinal) =>
            e("li", { key: `ini-host-${hostOrdinal}` },
              e("label", null, `Declared ${host.inventoryName} (address: ${host.reportedConnectionAddress ?? "UNKNOWN"}) · `,
                e("select", {
                  "data-ansible-ini-associate-host": String(hostOrdinal),
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
      ? e("p", { "data-ansible-ini-association-limit": "true" },
          `Only first ${DISPLAY_LIMIT} of ${preview.hosts.length} inventory hosts can be reviewed; all others remain unassociated.`)
      : null,
    duplicateTargets
      ? e("p", { role: "alert", "data-ansible-ini-association-conflict": "BLOCKED" },
          "Two INI inventory hosts cannot be assigned to the same modeled resource.")
      : null,
    e("p", null, `Explicit host associations: ${selected.length}. Unselected hosts remain unassociated.`),
    e("label", null,
      e("input", { type: "checkbox", "data-ansible-ini-association-ack": "true",
        checked: acknowledged, disabled: busy || submitting || !model || !selected.length || duplicateTargets,
        onChange: event => { setAcknowledged(event.target.checked); setExported(false); } }),
      " I acknowledge these are my unverified inventory-to-model associations, not independently verified asset identities."),
    e("button", { type: "button", "data-ansible-ini-association-export": "true",
      disabled: !canExport, onClick: () => { void submit(); } },
      submitting ? "Validating associations…" : "Export reviewed INI associations (JSON)"),
    error ? e("p", { role: "alert", "data-ansible-ini-association-error": "BLOCKED" }, error) : null,
    exported ? e("p", { "data-ansible-ini-association-exported": "true" },
      "INI association sidecar exported. Builder and Engine state were not modified.") : null);
}
