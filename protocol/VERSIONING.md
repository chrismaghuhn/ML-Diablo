# Protocol versioning

The bridge uses three independent versions:

- **Transport protocol** (`dxai.bridge.v1`): request ordering, errors and framing.
- **Observation contract** (`dxai.observation.v1`): information visible to the policy.
- **Action contract** (`dxai.action.v1`): semantic candidate payloads.

A field may be added compatibly only when old clients can safely ignore it. Changing meaning, units, visibility, candidate identity or terminal semantics requires a new contract version. During a migration the engine may support two adjacent versions, but a trajectory and checkpoint must declare exactly one version of each contract.

The `.proto` file is a logical schema. M0 may use length-prefixed Protobuf over a local socket, shared memory, or another local IPC implementation. The selected transport must preserve request IDs and reject stale step requests.
