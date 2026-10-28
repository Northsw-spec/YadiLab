import React, { useEffect, useRef, useState } from "react";
const e = React.createElement;
const DISPLAY_TABLES = 20;
const DISPLAY_ROWS = 30;
const DISPLAY_CELLS = 16;

export function DocxTableStructureDetails({ result }) {
  if (!result) return e("p", { "data-docx-empty": "true" },
    "Choose a local .docx file. This inspection deliberately displays no document cell text.");
  const { filename, preview } = result;
  return e("section", { className: "network-import-preview", "data-docx-preview": "CONFIG_DOCUMENTED" },
    e("h3", null, "DOCX table structure — ", filename),
    e("p", { "data-docx-summary": "true" },
      `Declared tables: ${preview.tables.length} · structural cells: ${preview.totalCells}`),
    e("p", { "data-docx-source-hash": "true" }, `Original SHA-256: ${preview.sourceSha256}`),
    e("p", { className: "helper-note", "data-docx-truth-boundary": "true" },
      "CONFIG_DOCUMENTED, REVIEW_REQUIRED. These are document table shapes only. No cell values, source secrets, identified machines, verified physical links, Builder changes or Engine PASS."),
    e("ol", { className: "validation-list", "data-docx-tables": "true" },
      ...preview.tables.slice(0, DISPLAY_TABLES).map((table) =>
        e("li", { key: table.tableOrdinal, "data-docx-table": String(table.tableOrdinal) },
          e("strong", null, `Table ${table.tableOrdinal + 1}: ${table.rows.length} rows`),
          e("ol", { className: "validation-list" },
            ...table.rows.slice(0, DISPLAY_ROWS).map((row) =>
              e("li", { key: row.rowOrdinal, "data-docx-row": `${table.tableOrdinal}:${row.rowOrdinal}` },
                `Row ${row.rowOrdinal + 1}: ${row.cells.length} cells`,
                e("ul", { className: "validation-list" },
                  ...row.cells.slice(0, DISPLAY_CELLS).map((cell) =>
                    e("li", { key: cell.cellOrdinal,
                        "data-docx-cell": `${table.tableOrdinal}:${row.rowOrdinal}:${cell.cellOrdinal}` },
                      `Cell ${cell.cellOrdinal + 1}: ${cell.textCodeUnits} text code units · source table ${cell.locator.tableOrdinal + 1}, row ${cell.locator.rowOrdinal + 1}, cell ${cell.locator.cellOrdinal + 1}`)),
                row.cells.length > DISPLAY_CELLS ? e("p", null, "Further cells not displayed.") : null))),
            table.rows.length > DISPLAY_ROWS
              ? e("li", { "data-docx-row-limit": "true" }, `Showing first ${DISPLAY_ROWS} of ${table.rows.length} rows.`) : null))),
    e("p", { "data-docx-activation-status": "BLOCKED" },
      "Read-only structure inspection. No DOCX-to-topology mapping or simulation activation. Close without changes."));
}

export function DocxTableStructurePanel({ inspectFile, onClose }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const currentRequest = useRef(0);
  const focus = useRef(null);
  useEffect(() => { focus.current?.focus(); return () => { currentRequest.current++; }; }, []);
  useEffect(() => {
    const escape = (event) => {
      if (event.key === "Escape" && !busy) { currentRequest.current++; onClose(); }
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [busy, onClose]);
  const choose = async (file) => {
    if (!file) return;
    const request = ++currentRequest.current;
    setResult(null); setError(""); setBusy(true);
    try {
      const next = await inspectFile(file);
      if (request === currentRequest.current) setResult(next);
    } catch (cause) {
      if (request === currentRequest.current) {
        const code = typeof cause?.code === "string" && /^(DOCX_|IMPORT_ARCHIVE_|IMPORT_WORKBOOK_ARCHIVE_|IMPORT_XML_)[A-Z_]+$/.test(cause.code)
          ? cause.code : "DOCX_INSPECTION_BLOCKED";
        setError(code);
      }
    } finally {
      if (request === currentRequest.current) setBusy(false);
    }
  };
  return e("div", { className: "network-import-overlay", "data-docx-overlay": "true" },
    e("section", { className: "network-import-panel", role: "dialog", "aria-modal": "true",
        "aria-label": "Word DOCX table structure inspection", ref: focus, tabIndex: -1,
        "data-docx-panel": "CONFIG_DOCUMENTED" },
      e("div", { className: "network-import-heading" },
        e("div", null,
          e("h2", null, "Inspect Word DOCX — structure only"),
          e("p", null, "Local offline analysis. No document text is shown or imported.")),
        e("button", { type: "button", disabled: busy, "aria-label": "Close Word DOCX inspection",
          onClick: () => { currentRequest.current++; onClose(); } }, "Close")),
      e("label", { className: "file-button" }, busy ? "Reading DOCX structure…" : "Choose .docx file",
        e("input", { type: "file", accept: ".docx", hidden: true, disabled: busy,
          "data-docx-file": "true", onChange: (event) => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (file) void choose(file);
          } })),
      error ? e("p", { role: "alert", className: "helper-status blocked",
        "data-docx-error": "BLOCKED" }, error) : null,
      e(DocxTableStructureDetails, { result }),
      e("div", { className: "network-import-actions" },
        e("button", { type: "button", disabled: busy, "data-docx-close": "true",
          onClick: () => { currentRequest.current++; onClose(); } }, "Close without changes"))));
}
