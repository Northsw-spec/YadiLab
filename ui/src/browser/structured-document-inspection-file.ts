import { inspectStructuredXmlFileReadOnly, type StructuredXmlReadableFile } from "./structured-xml-inspection-file.js";
import {
  inspectStaticAnsibleSourceReadOnly, type AnsibleStaticInspection,
} from "../../../enterprise-import/src/structured-ansible-source-inspection.js";
import { EnterpriseImportError } from "../../../enterprise-import/src/types.js";
import type { ReadOnlyXmlInspection } from "../../../enterprise-import/src/structured-xml-source-inspection.js";

export type SharedDocumentInspection = ReadOnlyXmlInspection | AnsibleStaticInspection;
const MAX_STATIC_BYTES = 256 * 1024;

/**
 * IC-010 P3a. Browser file bridge for exactly six producer-validated profiles:
 * 4 prior XML subsets and two static Ansible inventory subsets. Any future
 * suffix/format has no implicit authority from a planned registry entry.
 */
export async function inspectSharedDocumentFileReadOnly(
  file: StructuredXmlReadableFile,
): Promise<SharedDocumentInspection> {
  if (!file || typeof file.name !== "string" || typeof file.arrayBuffer !== "function" ||
      file.name.length < 1 || file.name.length > 255 ||
      file.name.trim() !== file.name ||
      /[\\/\u0000-\u001f\u007f]/.test(file.name)) {
    throw new EnterpriseImportError("IC010_P3_FILE_INVALID", "IC010_P3_FILE_INVALID");
  }
  const name = file.name.toLowerCase();
  const staticInventory = name.endsWith(".yaml") || name.endsWith(".yml") || name.endsWith(".ini");
  const xml = name.endsWith(".graphml") || name.endsWith(".drawio") ||
    name.endsWith(".nessus") || name.endsWith(".xml");
  if (!xml && !staticInventory) {
    throw new EnterpriseImportError("IC010_P3_EXTENSION_UNSUPPORTED", "IC010_P3_EXTENSION_UNSUPPORTED");
  }
  if (!staticInventory) {
    // Original XML contract and maximum source budget stay authoritative.
    return inspectStructuredXmlFileReadOnly(file);
  }
  if (file.size !== undefined &&
      (!Number.isSafeInteger(file.size) || file.size < 1 || file.size > MAX_STATIC_BYTES)) {
    throw new EnterpriseImportError("IC010_P3_SOURCE_SIZE_INVALID", "IC010_P3_SOURCE_SIZE_INVALID");
  }
  const raw: unknown = await file.arrayBuffer();
  if (!(raw instanceof ArrayBuffer) || raw.byteLength < 1 || raw.byteLength > MAX_STATIC_BYTES) {
    throw new EnterpriseImportError("IC010_P3_SOURCE_READ_INVALID", "IC010_P3_SOURCE_READ_INVALID");
  }
  return inspectStaticAnsibleSourceReadOnly(file.name, new Uint8Array(raw));
}
