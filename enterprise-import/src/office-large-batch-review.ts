import { previewDocxTableStructure,
  SCALE_OFFICE_LARGE_STRUCTURE_PROFILE as DOCX_LARGE_PROFILE,
  type DocxTableCellLocator } from "./docx-tables-structural-preview.js";
import { previewOdtTableStructure,
  SCALE_OFFICE_LARGE_STRUCTURE_PROFILE as ODT_LARGE_PROFILE,
  type OdtCellLocator } from "./odt-tables-structural-preview.js";
import { openSafeWorkbookArchive, productionWorkbookArchiveBackend,
  type WorkbookArchiveLimits } from "./workbook-archive.js";
import { childElements, parseSafeXml, type XmlNode } from "./xml-lite.js";
import { EnterpriseImportError } from "./types.js";

/**
 * SCALE-001 P1b1: consented, bounded, **source-only** Office batch disclosure.
 * NOT an import adapter or a Builder/Engine activation path. The frozen
 * P1a structural validation is run once per batch; the selected original
 * source cells are extracted in one additional ZIP/XML pass per batch,
 * NEVER one ZIP/XML reparse per cell. Old per-cell APIs are unchanged.
 */
export const OFFICE_SCALED_BATCH_PROFILE = "office.scaled-reviewed-batch.v1" as const;
export type OfficeScaledBatchFormat = "docx" | "odt";
export type OfficeScaledCellLocator = DocxTableCellLocator | OdtCellLocator;

export interface OfficeScaledColumnConsent {
  readonly cellOrdinal: number;
  readonly acknowledge: true;
}
export interface OfficeScaledBatchDecision {
  readonly format: OfficeScaledBatchFormat;
  readonly sourceSha256: string;
  readonly capacityProfile: typeof OFFICE_SCALED_BATCH_PROFILE;
  readonly tableOrdinal: number;
  /** Inclusive and intentionally excludes the source table header (row 0). */
  readonly rowStart: number;
  readonly rowEnd: number;
  readonly columns: readonly OfficeScaledColumnConsent[];
  readonly acknowledgeSelectedRange: true;
  readonly acknowledgeDisclosure: true;
}
export interface OfficeScaledDisclosedCell {
  readonly locator: OfficeScaledCellLocator;
  readonly text: string;
}
export interface OfficeScaledDisclosedRow {
  readonly rowOrdinal: number;
  readonly cells: readonly OfficeScaledDisclosedCell[];
}
export interface OfficeScaledBatchDisclosure {
  readonly status: "REVEALED_UNVERIFIED";
  readonly capacityProfile: typeof OFFICE_SCALED_BATCH_PROFILE;
  readonly sourceSha256: string;
  readonly tableOrdinal: number;
  readonly rows: readonly OfficeScaledDisclosedRow[];
  readonly canActivate: false;
  readonly engineVerified: false;
  readonly physicalTopologyVerified: false;
}
const SHA = /^[0-9a-f]{64}$/;
const MAX_SOURCE_BYTES = 16 * 1024 * 1024;
const MAX_BATCH_ROWS = 100;
const MAX_BATCH_COLUMNS = 4;
const DECISION_KEYS = ["format","sourceSha256","capacityProfile","tableOrdinal",
  "rowStart","rowEnd","columns","acknowledgeSelectedRange","acknowledgeDisclosure"];
const COLUMN_KEYS = ["cellOrdinal","acknowledge"];
const CREDENTIAL = /(?:password|passwd|passphrase|secret|token|credential|bearer|private|confidential|sensitive|api[ ._-]*key|access[ ._-]*key|ssh[ ._-]*key|authorization|connection[ ._-]*string|certificate[ ._-]*key)/i;
const LIMITS: Readonly<Record<OfficeScaledBatchFormat, WorkbookArchiveLimits>> = {
  docx: { maxFiles:128,maxCompressedBytes:16*1024*1024,
    maxDecompressedBytes:32*1024*1024,maxSingleFileBytes:4*1024*1024,
    maxCompressionRatio:100 },
  odt: { maxFiles:32,maxCompressedBytes:16*1024*1024,
    maxDecompressedBytes:32*1024*1024,maxSingleFileBytes:4*1024*1024,
    maxCompressionRatio:100 },
};

function deny(code: "SCALE_P1B1_SELECTION_INVALID" | "SCALE_P1B1_CONSENT_REQUIRED" |
  "SCALE_P1B1_SOURCE_CHANGED" | "SCALE_P1B1_SOURCE_BLOCKED" |
  "SCALE_P1B1_SENSITIVE_BLOCKED"): never {
  // Stable errors only: never attach source strings or raw archive exceptions.
  throw new EnterpriseImportError(code, code);
}
const ordinal = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number)>=0;
const exact = (v: unknown, keys: readonly string[]): boolean =>
  !!v && typeof v === "object" && !Array.isArray(v) &&
  Object.keys(v).sort().join(",") === [...keys].sort().join(",");
function isSensitive(value: string): boolean {
  return value.length < 1 || value.length > 128 ||
    !/^[A-Za-z0-9][A-Za-z0-9 ._:-]*$/.test(value) ||
    CREDENTIAL.test(value) ||
    /[A-Za-z0-9_-]{24,}/.test(value) ||
    /(?:[A-Fa-f0-9]{2}:){8,}[A-Fa-f0-9]{2}/.test(value);
}
function selectedText(format: OfficeScaledBatchFormat, node: XmlNode): string {
  return format === "docx"
    ? childElements(node,"p").flatMap(p=>childElements(p,"r").flatMap(r=>
      childElements(r,"t").map(t=>t.text))).join("")
    : childElements(node,"p").map(p=>p.text).join("");
}
function validateDecision(input: unknown): asserts input is OfficeScaledBatchDecision {
  if(!input||typeof input!=="object"||Array.isArray(input))
    deny("SCALE_P1B1_SELECTION_INVALID");
  const d=input as Partial<OfficeScaledBatchDecision>;
  if(d.acknowledgeSelectedRange!==true || d.acknowledgeDisclosure!==true ||
    (Array.isArray(d.columns) && d.columns.some(c=>c?.acknowledge!==true)))
    deny("SCALE_P1B1_CONSENT_REQUIRED");
  if(!exact(d,DECISION_KEYS) || (d.format!=="docx"&&d.format!=="odt") ||
    d.capacityProfile!==OFFICE_SCALED_BATCH_PROFILE ||
    typeof d.sourceSha256!=="string" || !SHA.test(d.sourceSha256) ||
    !ordinal(d.tableOrdinal) || d.tableOrdinal>=20 ||
    !ordinal(d.rowStart) || d.rowStart<1 ||
    !ordinal(d.rowEnd) || d.rowEnd<d.rowStart || d.rowEnd>1000 ||
    d.rowEnd-d.rowStart+1>MAX_BATCH_ROWS ||
    !Array.isArray(d.columns) || d.columns.length<1 ||
    d.columns.length>MAX_BATCH_COLUMNS)
    deny("SCALE_P1B1_SELECTION_INVALID");
  const seen=new Set<number>();
  for(const col of d.columns) {
    if(!exact(col,COLUMN_KEYS) || !ordinal(col.cellOrdinal) ||
      col.cellOrdinal>=16 || seen.has(col.cellOrdinal))
      deny("SCALE_P1B1_SELECTION_INVALID");
    seen.add(col.cellOrdinal);
  }
}

/**
 * Deliberately copied input preserves a coherent original-byte snapshot even
 * if the caller later mutates its own Uint8Array while async ZIP code runs.
 * Caller must still independently compare the actual original File and active
 * workspace immediately before any future Builder mutation (P1b2).
 */
export async function revealReviewedOfficeBatch(
  original: Uint8Array,
  decision: OfficeScaledBatchDecision,
): Promise<OfficeScaledBatchDisclosure> {
  validateDecision(decision);
  if(!(original instanceof Uint8Array) || original.byteLength<4 ||
    original.byteLength>MAX_SOURCE_BYTES)
    deny("SCALE_P1B1_SELECTION_INVALID");
  const bytes=Uint8Array.from(original);
  let preview;
  try {
    preview=decision.format==="docx"
      ? await previewDocxTableStructure(bytes,{capacityProfile:DOCX_LARGE_PROFILE})
      : await previewOdtTableStructure(bytes,{capacityProfile:ODT_LARGE_PROFILE});
  } catch {
    deny("SCALE_P1B1_SOURCE_BLOCKED");
  }
  if(preview.sourceSha256!==decision.sourceSha256)
    deny("SCALE_P1B1_SOURCE_CHANGED");
  const table=preview.tables[decision.tableOrdinal];
  if(!table || table.rows.length<=decision.rowEnd || !table.rows[0])
    deny("SCALE_P1B1_SELECTION_INVALID");
  // Check every structural cell before opening the source for selection.
  for(let r=decision.rowStart;r<=decision.rowEnd;r++) {
    if(!table.rows[r] || decision.columns.some(c=>
      !table.rows[r]?.cells[c.cellOrdinal]) ||
      decision.columns.some(c=>!table.rows[0]?.cells[c.cellOrdinal]))
      deny("SCALE_P1B1_SELECTION_INVALID");
  }
  let archive;
  try {
    archive=await openSafeWorkbookArchive(bytes,productionWorkbookArchiveBackend(),
      LIMITS[decision.format]);
    const xml=await archive.read(decision.format==="docx"
      ? "word/document.xml" : "content.xml");
    const root=parseSafeXml(xml,"SCALE-001 validated Office batch");
    const body=childElements(root,"body")[0];
    const holder=decision.format==="docx" ? body :
      body&&childElements(body,"text")[0];
    const tableNodes=holder&&childElements(holder,
      decision.format==="docx"?"tbl":"table");
    const originalTable=tableNodes?.[decision.tableOrdinal];
    const rows=originalTable&&childElements(originalTable,
      decision.format==="docx"?"tr":"table-row");
    if(!rows||rows.length<=decision.rowEnd)
      deny("SCALE_P1B1_SELECTION_INVALID");
    const cellsFor=(row:XmlNode)=>childElements(row,
      decision.format==="docx"?"tc":"table-cell");
    const header=cellsFor(rows[0]!);
    const inspected:OfficeScaledDisclosedRow[]=[];
    for(let r=decision.rowStart;r<=decision.rowEnd;r++){
      const originals=cellsFor(rows[r]!);
      const label=originals[0] ? selectedText(decision.format,originals[0]) : "";
      if(CREDENTIAL.test(label)) deny("SCALE_P1B1_SENSITIVE_BLOCKED");
      const selected:OfficeScaledDisclosedCell[]=[];
      for(const column of decision.columns){
        const ordinal=column.cellOrdinal;
        const heading=header[ordinal]?selectedText(decision.format,header[ordinal]!):"";
        if(CREDENTIAL.test(heading))
          deny("SCALE_P1B1_SENSITIVE_BLOCKED");
        const sourceCell=originals[ordinal];
        const expected=table.rows[r]?.cells[ordinal];
        if(!sourceCell||!expected)
          deny("SCALE_P1B1_SELECTION_INVALID");
        const value=selectedText(decision.format,sourceCell);
        if(value.length!==expected.textCodeUnits)
          deny("SCALE_P1B1_SOURCE_BLOCKED");
        if(isSensitive(value))
          deny("SCALE_P1B1_SENSITIVE_BLOCKED");
        selected.push(Object.freeze({
          locator:Object.freeze({...expected.locator}),
          text:value,
        }));
      }
      inspected.push(Object.freeze({
        rowOrdinal:r,cells:Object.freeze(selected),
      }));
    }
    return Object.freeze({
      status:"REVEALED_UNVERIFIED",
      capacityProfile:OFFICE_SCALED_BATCH_PROFILE,
      sourceSha256:preview.sourceSha256,
      tableOrdinal:decision.tableOrdinal,
      rows:Object.freeze(inspected),
      canActivate:false,engineVerified:false,physicalTopologyVerified:false,
    });
  }catch(error){
    if(error instanceof EnterpriseImportError && /^SCALE_P1B1_/.test(error.code))
      throw error;
    deny("SCALE_P1B1_SOURCE_BLOCKED");
  }finally{
    if(archive) await archive.close().catch(()=>{});
  }
  // Statically exhaustive fail-closed fallback: no implicit undefined return.
  return deny("SCALE_P1B1_SOURCE_BLOCKED");
}
