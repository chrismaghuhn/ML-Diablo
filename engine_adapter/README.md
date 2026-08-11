# Standalone engine-adapter contract

This directory deliberately contains **no DevilutionX code**. It defines and tests the narrow C++ contract that an integration patch must implement.

The [`observation_probe`](observation_probe/) subdirectory is the first
M0.2 integration slice. It is a separately built, read-only executable that
links against a user-owned pinned DevilutionX build. It exports one structured
observation and intentionally has no candidate execution, `step` endpoint or
IPC server yet.

The production adapter belongs in a private/non-commercial DevilutionX checkout or a clearly marked derivative that obeys the upstream Sustainable Use License. The recommended implementation is compiled into a dedicated headless executable and communicates with Python over a versioned local IPC protocol. Do not expose engine globals directly to Python and do not drive the game through mouse coordinates.

Integration acceptance gates are specified in `docs/04_DEVILUTIONX_INTEGRATION.md` and `docs/contracts/`.
