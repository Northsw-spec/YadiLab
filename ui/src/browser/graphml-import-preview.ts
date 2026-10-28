import { previewGraphmlReadOnly, type GraphmlReadOnlyPreview } from "../../../enterprise-import/src/graphml-preview.js";
import { EnterpriseImportError } from "../../../enterprise-import/src/types.js";

const MAX_GRAPHML_BYTES = 2 * 1024 * 1024;

/** Minimal file interface, keeping the browser boundary independent of DOM types. */
export interface GraphmlReadableFile {
  readonly name: string;
  readonly size?: number;
  arrayBuffer(): Promise<ArrayBuffer>;
}

export interface GraphmlFilePreview {
  readonly filename: string;
  readonly preview: GraphmlReadOnlyPreview;
}

/**
 * Preview only: never creates a YadiLab scenario, cable, route, active
 * workspace or Engine evaluation. Validation of GraphML structural bytes
 * remains the responsibility of previewGraphmlReadOnly.
 */
export async function previewGraphmlFileReadOnly(file: GraphmlReadableFile): Promise<GraphmlFilePreview> {
  if (!file || typeof file.name !== "string" ||
      !/^[^/\\\0]+\.graphml$/i.test(file.name)) {
    throw new EnterpriseImportError("GRAPHML_FILE_EXTENSION_INVALID", "Choose one .graphml file; no alternate XML profiles are assumed.");
  }
  if (file.size !== undefined && (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > MAX_GRAPHML_BYTES)) {
    throw new EnterpriseImportError("GRAPHML_FILE_SIZE_INVALID", "GraphML file must be nonempty and at most 2 MiB.");
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes.byteLength === 0 || bytes.byteLength > MAX_GRAPHML_BYTES) {
    throw new EnterpriseImportError("GRAPHML_FILE_SIZE_INVALID", "GraphML file must be nonempty and at most 2 MiB.");
  }
  return { filename: file.name, preview: await previewGraphmlReadOnly(bytes) };
}
