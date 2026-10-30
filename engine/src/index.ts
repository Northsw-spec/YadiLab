export type {
  AuthenticationDetails,
  ConntrackDecisionTrace,
  ConntrackEntryDisposition,
  ConntrackEntryTrace,
  ConntrackState,
  DhcpClientStateRead,
  DhcpDoraDecisionTrace,
  DhcpDoraStageKind,
  DhcpDoraStageTrace,
  DhcpServerAttemptTrace,
  DhcpServerDisposition,
  DnsChainDecisionTrace,
  DnsConfiguredResolversState,
  DnsResolverAttemptTrace,
  DnsResolverDisposition,
  DnsResolverStateRead,
  EngineDiagnostic,
  EngineEvaluation,
  EngineQueryResult,
  EngineState,
  EvidenceEvent,
  FindingEvaluation,
  ForwardReturnPathComparisonTrace,
  HostListenerConsistency,
  HostProcessTrace,
  HostServiceTrace,
  HostSocketBindScope,
  HostSocketState,
  HostSocketTrace,
  HostStackDecisionTrace,
  HostStackModel,
  ListenerServiceDecisionTrace,
  ListenerServiceDisposition,
  ListenerServiceModel,
  ListenerStateRead,
  ServiceStateRead,
  TcpLifecycleState,
  TcpSocketStateTrace,
  TcpStateMachineDecisionTrace,
  UdpIcmpFailureDecisionTrace,
  UdpIcmpFailureDisposition,
  TcpStateMachineDisposition,
  TcpStateMachineModel,
  TcpStateTransitionTrace,
  TcpTelemetryStatus,
  MacCandidateDisposition,
  MacCandidateTrace,
  MacDecisionTrace,
  MacForwardingDisposition,
  MacLearningDisposition,
  MembershipDetails,
  NatDecisionKind,
  NatDecisionTrace,
  NatRuleDisposition,
  NatRuleTrace,
  NatTransformationDisposition,
  NeighborCandidateDisposition,
  NeighborCandidateTrace,
  NeighborDecisionTrace,
  NeighborProtocol,
  NeighborState,
  ObjectiveEvaluation,
  OperationResult,
  PermissionDetails,
  PolicyDecisionKind,
  PolicyDecisionTrace,
  PolicyRuleDisposition,
  PolicyRuleTrace,
  ReachabilityDetails,
  ReturnSecurityStatus,
  ReturnPathEvaluationMode,
  PathSymmetry,
  PathInterfaceComparisonTrace,
  RouteCandidateDisposition,
  RouteCandidateTrace,
  RouteDecisionTrace,
  RuleEvaluationContext,
  RuntimeResourceState,
  L2PropagationCounters,
  L2PropagationEvent,
  L2PropagationEventKind,
  L2PropagationOutcome,
  L2PropagationResult,
  MtuComparisonOutcome,
  MtuEvaluationRequest,
  MtuEvaluationTrace,
  MtuFragmentationDisposition,
  MtuIcmpDisposition,
  ScenarioOperation,
  ScenarioResource,
  ScenarioTest,
  TestEvaluation,
  TruthValue,
  StpBpduDisposition,
  StpDecisionTrace,
  StpPathDisposition,
  StpPortRole,
  StpPortState,
  StpPortTrace,
  StpProtocol,
  VlanDecisionTrace,
  VlanPortDisposition,
  VlanPortMode,
  VlanPortTrace,
  VlanRewriteDisposition,
  VlanTagState,
} from "./types.js";
export { simulateL2RepeatedPropagation } from "./l2-storm-engine.js";
export type { L2PropagationOptions } from "./l2-storm-engine.js";
export { derivePathMtu, evaluateMtuAtEgress } from "./mtu-engine.js";

export { truthAll, truthAny, truthEquals, truthNot } from "./truth.js";
export { readPath, removePath, setPath } from "./path.js";
export { createInitialEngineState, applyOperation, applyOperations } from "./state.js";
export { SIMULATION_EVENT_PLAN_FORMAT, SIMULATION_EVENT_PLAN_SCHEMA_VERSION, SIMULATION_EVENT_QUEUE_LIMIT, createSimulationEventPlan, inspectSimulationEventPlan, scheduleSimulationEvent, cancelSimulationEvent, advanceSimulationEventPlan } from "./simulation-clock.js";
export { SIMULATION_TRANSITION_FORMAT, SIMULATION_TRANSITION_VERSION, SIMULATION_MARKER_KIND, SIMULATION_MARKER_PROVENANCE, createSimulationTransitionState, inspectSimulationTransitionState, scheduleSimulationMarker, cancelSimulationMarker, advanceSimulationTransitions } from "./simulation-transitions.js";
export { OSPF_P2P_FORMAT, OSPF_P2P_VERSION, OSPF_P2P_MAX_EVENTS, OSPF_P2P_MAX_ADVANCE_EVENTS, createOspfP2pSession, inspectOspfP2pSession, receiveOspfP2pHello, advanceOspfP2pSession } from "./ospf-p2p-hello.js";
export type { OspfP2pNeighborState, OspfP2pTraceKind, OspfP2pConfig, OspfP2pHelloObservation, OspfP2pTrace, OspfP2pSession, OspfP2pResult } from "./ospf-p2p-hello.js";
export type { SimulationMarkerReceipt, SimulationMarkerCancellation, SimulationTransitionState, SimulationMarkerRequest, SimulationTransitionResult } from "./simulation-transitions.js";
export type { ScheduledSimulationEvent, SimulationEventPlan, SimulationEventPlanResult, NewSimulationEvent } from "./simulation-clock.js";
export { queryServiceEnabled, queryListeningPort, queryListenerServiceState, queryHostStackView } from "./service-engine.js";
export { queryTcpStateMachine } from "./tcp-engine.js";
export { sourceDefaultGatewayVerdict, queryReachabilityWithSourceGateway } from "./source-gateway-engine.js";
export { withUdpIcmpFailureDiagnostic, validateUdpIcmpFailureDecision } from "./udp-icmp-engine.js";
export { normalizeDnsQueryName, queryDnsChain } from "./dns-engine.js";
export { queryDhcpDora } from "./dhcp-engine.js";
export { queryLayer2BroadcastReachability, queryReachability } from "./network-engine.js";
export { queryAuthentication, queryMembership, queryPermission } from "./identity-engine.js";
export { evaluateRule } from "./rule-engine.js";
export { evaluateTest } from "./test-engine.js";
export { evaluateEngine } from "./evaluation.js";
export { replayCanonicalSolution, runScenarioRegression } from "./regression.js";
export { createSaveState, restoreSaveState } from "./save-state.js";
export type { RestoreSaveFailure, RestoreSaveResult, RestoreSaveSuccess } from "./save-state.js";
export type { CanonicalReplayResult, RegressionCheck, RegressionCheckKind, RegressionPhase, ScenarioRegressionReport } from "./regression.js";

export { ENGINE_VERSION } from "./version.js";
