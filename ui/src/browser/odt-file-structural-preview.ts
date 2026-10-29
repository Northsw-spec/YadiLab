import { previewOdtTableStructure, type OdtStructuralPreview } from "../../../enterprise-import/src/odt-tables-structural-preview.js";
import { EnterpriseImportError } from "../../../enterprise-import/src/types.js";

const MAX_BYTES=16*1024*1024;
export interface OdtLocalFile {
  readonly name:string;
  readonly size?:number;
  arrayBuffer():Promise<ArrayBuffer>;
}
export interface OdtLocalStructure {
  readonly filename:string;
  readonly preview:OdtStructuralPreview;
}
/** Offline local file bridge; extension alone NEVER authorizes parsing. */
export async function previewOdtFileStructure(file:OdtLocalFile):Promise<OdtLocalStructure> {
  if(!file || typeof file.name!=="string" || file.name.length>240 ||
    !/^[^/\\\0]+\.odt$/i.test(file.name) || typeof file.arrayBuffer!=="function"){
    throw new EnterpriseImportError("ODT_FILE_EXTENSION_INVALID","ODT_FILE_EXTENSION_INVALID");
  }
  if(file.size!==undefined &&
      (!Number.isSafeInteger(file.size)||file.size<42||file.size>MAX_BYTES)){
    throw new EnterpriseImportError("ODT_FILE_SIZE_INVALID","ODT_FILE_SIZE_INVALID");
  }
  const buffer=await file.arrayBuffer();
  if(!(buffer instanceof ArrayBuffer)||buffer.byteLength<42||buffer.byteLength>MAX_BYTES){
    throw new EnterpriseImportError("ODT_FILE_SIZE_INVALID","ODT_FILE_SIZE_INVALID");
  }
  return {filename:file.name,preview:await previewOdtTableStructure(new Uint8Array(buffer))};
}
