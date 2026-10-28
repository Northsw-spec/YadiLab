import { previewDocxTableStructure, type DocxStructuralPreview } from "../../../enterprise-import/src/docx-tables-structural-preview.js";
import { EnterpriseImportError } from "../../../enterprise-import/src/types.js";

const MAX_BYTES = 16 * 1024 * 1024;
export interface DocxLocalFile {
  readonly name: string;
  readonly size?: number;
  arrayBuffer(): Promise<ArrayBuffer>;
}
export interface DocxLocalPreview {
  readonly filename: string;
  readonly preview: DocxStructuralPreview;
}

/**
 * File picker bridge only. Never uploads, fetches, interprets cell content
 * or mutates Builder/Engine. The strict ZIP+WordprocessingML domain parser
 * independently validates the complete input; extension is just a UI filter.
 */
export async function previewDocxFileStructure(file: DocxLocalFile): Promise<DocxLocalPreview> {
  if (!file || typeof file.name !== "string" ||
      !/^[^/\\\0]+\.docx$/i.test(file.name) || typeof file.arrayBuffer !== "function" ||
      file.name.length > 240) {
    throw new EnterpriseImportError("DOCX_FILE_EXTENSION_INVALID", "Select one local .docx file.");
  }
  if (file.size !== undefined &&
      (!Number.isSafeInteger(file.size) || file.size < 4 || file.size > MAX_BYTES)) {
    throw new EnterpriseImportError("DOCX_FILE_SIZE_INVALID", "DOCX must be nonempty and at most 16 MiB.");
  }
  const buffer = await file.arrayBuffer();
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 4 || buffer.byteLength > MAX_BYTES) {
    throw new EnterpriseImportError("DOCX_FILE_SIZE_INVALID", "DOCX must be nonempty and at most 16 MiB.");
  }
  return { filename: file.name, preview: await previewDocxTableStructure(new Uint8Array(buffer)) };
}
