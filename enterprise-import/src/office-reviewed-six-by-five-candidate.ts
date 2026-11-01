import type {OfficeReviewedLinkRowsCandidate,OfficeReviewedLinkRowsDecision} from "./office-reviewed-link-row-candidate.js";
import {mapReviewedOfficeOriginalToLinkRows} from "./office-reviewed-link-row-candidate.js";
import {OFFICE_REVIEWED_NODES_PROFILE} from "./office-reviewed-node-candidate.js";

export const OFFICE_REVIEWED_SIX_BY_FIVE_PROFILE=
  "office.reviewed-network-tables.six-by-five.v1" as const;
export const OFFICE_REVIEWED_SIX_BY_FIVE_OPTIONAL_PORTS_PROFILE=
  "office.reviewed-network-tables.six-by-five-optional-ports.v1" as const;
export interface OfficeReviewedSixByFiveDecision extends OfficeReviewedLinkRowsDecision {
  readonly capacityProfile: string;
}
export interface OfficeReviewedSixByFiveCandidate extends OfficeReviewedLinkRowsCandidate {
  readonly capacityProfile: typeof OFFICE_REVIEWED_SIX_BY_FIVE_PROFILE |
    typeof OFFICE_REVIEWED_SIX_BY_FIVE_OPTIONAL_PORTS_PROFILE;
}
const exactly=(v:unknown,keys:readonly string[]):boolean=>
  !!v&&typeof v==="object"&&!Array.isArray(v)&&
  Object.keys(v).sort().join(",")===[...keys].sort().join(",");
const keys=["format","sourceSha256","nodes","acknowledgeModeledResources",
  "linkRows","acknowledgeModeledLinkRows","capacityProfile"];
function blocked(
 sha:string,code:string,
 profile:OfficeReviewedSixByFiveCandidate["capacityProfile"]=OFFICE_REVIEWED_SIX_BY_FIVE_PROFILE,
):OfficeReviewedSixByFiveCandidate {
 return {
  status:"BLOCKED",profileId:OFFICE_REVIEWED_NODES_PROFILE,
  sourceSha256:sha,capacityProfile:profile,
  selectedResources:0,selectedConnections:0,origins:[],connectionOrigins:[],
  linkRowOrigins:[],portOrigins:[],canActivate:false,engineVerified:false,
  physicalTopologyVerified:false,diagnostics:[{code}],
 };
}
/** P5 and P6 require distinct opt-in profiles; all P4/P1b/P2/P3 exact-shape contracts remain unchanged. */
export async function mapReviewedOfficeOriginalToSixByFive(
 original:Uint8Array,decision:OfficeReviewedSixByFiveDecision,
):Promise<OfficeReviewedSixByFiveCandidate> {
 const sha=typeof decision?.sourceSha256==="string"&&/^[0-9a-f]{64}$/.test(decision.sourceSha256)
   ?decision.sourceSha256:"";
 const optionalPorts=decision?.capacityProfile===
   OFFICE_REVIEWED_SIX_BY_FIVE_OPTIONAL_PORTS_PROFILE;
 const profile=optionalPorts?OFFICE_REVIEWED_SIX_BY_FIVE_OPTIONAL_PORTS_PROFILE:
   OFFICE_REVIEWED_SIX_BY_FIVE_PROFILE;
 if(!exactly(decision,keys)||
    (decision?.capacityProfile!==OFFICE_REVIEWED_SIX_BY_FIVE_PROFILE && !optionalPorts))
   return blocked(sha,"IC040_P5_CAPACITY_PROFILE_INVALID");
 const invalid=optionalPorts?"IC040_P6_CAPACITY_DECISION_INVALID":
   "IC040_P5_CAPACITY_DECISION_INVALID";
 if(!Array.isArray(decision.nodes)||decision.nodes.length!==6||
   !Array.isArray(decision.linkRows)||decision.linkRows.length!==5||
   decision.acknowledgeModeledResources!==true||
   decision.acknowledgeModeledLinkRows!==true||
   decision.linkRows.some(r=>{
     if(!r||typeof r!=="object")return true;
     const absent=r.sourcePortCellOrdinal===null&&r.targetPortCellOrdinal===null&&
       r.acknowledgeSourcePortCell===false&&r.acknowledgeTargetPortCell===false;
     const present=r.sourcePortCellOrdinal!==null&&r.targetPortCellOrdinal!==null&&
       r.acknowledgeSourcePortCell===true&&r.acknowledgeTargetPortCell===true;
     // Let P4 retain its stable exact one-sided-port denial code.
     const oneSided=(r.sourcePortCellOrdinal===null)!==(r.targetPortCellOrdinal===null);
     return optionalPorts?(oneSided?false:!(absent||present)):!present;
   }))return blocked(sha,invalid,profile);
 const legacy:OfficeReviewedLinkRowsDecision={
   format:decision.format,sourceSha256:sha,nodes:decision.nodes,
   acknowledgeModeledResources:decision.acknowledgeModeledResources,
   linkRows:decision.linkRows,
   acknowledgeModeledLinkRows:decision.acknowledgeModeledLinkRows,
 };
 const mapped=await mapReviewedOfficeOriginalToLinkRows(original,legacy,{
   maxNodes:6,maxLinks:5,
 });
 if(mapped.status!=="READY_FOR_COMPILATION"||!mapped.source)
   return {...mapped,capacityProfile:profile};
 return {...mapped,capacityProfile:profile};
}
