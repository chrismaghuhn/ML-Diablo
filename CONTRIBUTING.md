# Contributing

## Change discipline

Keep engine, protocol, data and ML changes separable. A pull request should normally touch one boundary at a time.

Before opening a change:

```bash
python -m pytest
python scripts/validate_artifacts.py
cmake -S engine_adapter -B build/bridge -DCMAKE_BUILD_TYPE=Release
cmake --build build/bridge --config Release
ctest --test-dir build/bridge -C Release --output-on-failure
```

## Contract changes

Any change to an observation, action, transition, episode manifest, checkpoint manifest, task ID or reward component requires:

1. a schema-version decision;
2. updated examples;
3. backward-compatibility notes;
4. migration or explicit rejection behavior;
5. contract tests;
6. an ADR if the semantics change.

Never silently reinterpret an existing field.

## ML claims

Do not describe an agent as "better" without a frozen evaluation suite, at least three training seeds, confidence intervals or per-seed results, and a comparison against the relevant baselines.

## Upstream code

Do not copy DevilutionX source into this standalone repository. Integrate through a separate fork/patch workflow and preserve upstream licensing notices.
