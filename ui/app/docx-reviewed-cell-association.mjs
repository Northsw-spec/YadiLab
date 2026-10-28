import React, { useState } from "react";
const e = React.createElement;

/**
 * Export ONE source locator -> existing modeled resource sidecar. Selected
 * cell value never becomes sidecar text; no direct Builder/Engine access.
 */
export function DocxReviewedCellAssociation({ disclosed, model, onExportAssociation }) {
  const [resourceId, setResourceId] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [exported, setExported] = useState(false);
  const canExport = Boolean(model && model.resources.length && disclosed &&
    resourceId && acknowledged && !submitting && typeof onExportAssociation === "function");
  const submit = async () => {
    if (!canExport) return;
    setSubmitting(true); setError(""); setExported(false);
    try {
      await onExportAssociation(disclosed, {
        sourceSha256: disclosed.sourceSha256,
        scenarioId: model.scenarioId,
        sourceRevision: model.sourceRevision,
        targetResourceId: resourceId,
        acknowledgeNotVerified: acknowledged,
      });
      setExported(true);
    } catch (cause) {
      // Display only our stable review codes, never file text/error messages.
      const code = typeof cause?.code === "string" && /^DOCX_[A-Z_]+$/.test(cause.code)
        ? cause.code : "DOCX_ASSOC_EXPORT_BLOCKED";
      setError(code);
    } finally {
      setSubmitting(false);
    }
  };
  return e("section", { className: "network-import-preview",
      "data-docx-association": "REVIEWED_ASSOCIATIONS_ONLY" },
    e("h4", null, "Optional reviewed reference to a modeled resource"),
    e("p", { "data-docx-association-boundary": "true" },
      "This is your UNVERIFIED reference from this ONE document cell to an existing Builder resource. JSON contains the cell position and file SHA-256, not the cell text. No Builder/Engine changes."),
    model && model.resources.length ? e("label", null, "Existing Builder resource: ",
      e("select", { "data-docx-association-target": "true", value: resourceId,
          disabled: submitting, onChange: event => {
            setResourceId(event.currentTarget.value);
            setAcknowledged(false); setExported(false); setError("");
          }},
        e("option", { value: "" }, "No resource selected (default)"),
        ...model.resources.map(resource => e("option", { key: resource.id, value: resource.id },
          resource.label + " [" + resource.id + "]"))))
      : e("p", { "data-docx-association-model-blocked": "true" },
        "An existing Builder scenario is required. Runtime observation is read-only."),
    e("label", null,
      e("input", { type: "checkbox", "data-docx-association-ack": "true",
        checked: acknowledged, disabled: !resourceId || !model || submitting,
        onChange: event => { setAcknowledged(event.currentTarget.checked); setExported(false); } }),
      " I assert this is an unverified operator-selected reference, not proof of the resource identity."),
    e("button", { type: "button", "data-docx-association-export": "true",
      disabled: !canExport, onClick: () => { void submit(); } },
      submitting ? "Revalidating original DOCX..." : "Export reviewed DOCX reference (JSON)"),
    error ? e("p", { role: "alert", "data-docx-association-error": "BLOCKED" }, error) : null,
    exported ? e("p", { "data-docx-association-exported": "true" },
      "One reference sidecar exported. Builder and Engine are unchanged.") : null);
}
