import { previewNessusFileReadOnly, type NessusReadableFile } from "./nessus-v2-file-preview.js";
import { reviewNessusHostReferences, type NessusHostReviewDecision,
  type NessusBuilderSnapshot, type NessusReviewedHostSidecar } from "../../../enterprise-import/src/nessus-association-review.js";
import type { NessusSeveritySummary } from "../../../enterprise-import/src/nessus-v2-preview.js";
import { EnterpriseImportError } from "../../../enterprise-import/src/types.js";
const deny=(code:string):never=>{throw new EnterpriseImportError(code,code);};

/** Never trust prior UI summary; re-read full original and compare source identity. */
export async function reviewNessusOriginalFileAssociations(
  file:NessusReadableFile,expected:NessusSeveritySummary,
  model:NessusBuilderSnapshot|null,decision:NessusHostReviewDecision,
):Promise<NessusReviewedHostSidecar>{
  if(!model)deny("NESSUS_ASSOC_BUILDER_REQUIRED");
  if(!decision||decision.acknowledgeNotVerified!==true)deny("NESSUS_ASSOC_ACK_REQUIRED");
  if(!expected || expected.status!=="EVIDENCE_ONLY" ||
     expected.semanticTrack!=="EVIDENCE_OBSERVED")deny("NESSUS_ASSOC_SOURCE_INVALID");
  const current=await previewNessusFileReadOnly(file);
  if(current.sourceSha256!==expected.sourceSha256||
     current.hostCount!==expected.hostCount||
     current.findingCount!==expected.findingCount||
     current.severityCounts.some((count,index)=>count!==expected.severityCounts[index])){
    deny("NESSUS_ASSOC_SOURCE_CHANGED");
  }
  const reviewed=reviewNessusHostReferences(current,model,decision);
  if(reviewed.status==="READY_FOR_EXPORT")return reviewed.sidecar;
  return deny(reviewed.diagnostics[0]?.code??"NESSUS_ASSOC_BLOCKED");
}
