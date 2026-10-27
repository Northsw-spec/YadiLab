import type { ScenarioSource } from "../../../core-model/src/generated/contracts.js";
import { mapNetworkWorkbookToScenario, normalizeNetworkInventoryDocument, selectEnterpriseImportAdapter } from "../../../enterprise-import/src/index.js";
import type { ImportDiagnostic } from "../../../enterprise-import/src/types.js";
import { readEnterpriseImportFile, type BinaryReadableFile } from "./import-helper.js";

export interface NetworkTopologyImportPreview {
  readonly ok: boolean;
  readonly source?: ScenarioSource;
  readonly filename: string;
  readonly sheets: readonly string[];
  readonly devices: number;
  readonly links: number;
  readonly diagnostics: readonly ImportDiagnostic[];
}

export async function previewNetworkTopologyFile(file: BinaryReadableFile): Promise<NetworkTopologyImportPreview> {
  const input = await readEnterpriseImportFile(file);
  const adapter = selectEnterpriseImportAdapter(input.mediaType);
  const parsed = await adapter.parse(input, { options: { tableName: "Devices" } });
  const normalized = normalizeNetworkInventoryDocument(parsed.document);
  const mapped = mapNetworkWorkbookToScenario(normalized.document);
  const diagnostics = [...parsed.diagnostics, ...normalized.diagnostics, ...mapped.diagnostics];
  const ok = mapped.ok && !diagnostics.some((x) => x.severity === "error") && Boolean(mapped.source);
  return { ok, ...(ok && mapped.source ? { source: mapped.source } : {}), filename: file.name,
    sheets: parsed.document.tables.map((x) => x.tableId), devices: mapped.source?.resources.length ?? normalized.document.tables.find((t) => t.tableId === "Nodes")?.records.length ?? 0,
    links: mapped.source?.connections.length ?? normalized.document.tables.find((t) => t.tableId === "Links")?.records.length ?? 0,
    diagnostics };
}
