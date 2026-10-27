# Dev29 firewall/NAT living-visualization truth contract

Dev29 preserves the existing Engine-first projection boundary for policy, NAT/PAT and conntrack. `policy.decision`, `nat.transform`, and `conntrack.lookup` events are projected only from validated Engine traces. A UI frame may highlight only the trace's proven connection/resource IDs; it cannot infer an allow, deny, translation, or session state from labels.

Malformed ACL, NAT, and conntrack models remain `UNKNOWN` and are rendered as uncertainty. Return-path security remains explicitly `RETURN_TUPLE_REQUIRED` when the model does not contain enough state; the visualization must not imply a successful reverse flow.
