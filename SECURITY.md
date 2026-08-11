# Security policy

This project executes a locally modified game engine and may load untrusted checkpoints, trajectory files, YAML and game data. Treat all of them as untrusted input.

- Do not use Python pickle for portable checkpoints or trajectories.
- Do not load arbitrary Torch objects with unrestricted deserialization.
- Prefer `safetensors` for model weights and JSON for metadata.
- Validate protocol message sizes before allocation.
- Bind engine workers to loopback only.
- Never accept remote bridge connections by default.
- Run fuzz and size-limit tests on the wire decoder before exposing it to external processes.

Report security issues privately to the repository owner rather than attaching malicious files to a public issue.
