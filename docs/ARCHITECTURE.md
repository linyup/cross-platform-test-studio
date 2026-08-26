# Architecture

The studio separates portable assets, execution policy and platform mechanics.

```text
Flow JSON -> validation -> FlowRunner -> Driver
                                      |-- Playwright desktop
                                      |-- ADB Android
                                      |-- WDA iOS
                                      `-- deterministic simulation
```

Selectors contain an ordered list of declared alternatives. Drivers may try those alternatives but must not ask a model to improvise during regression. AI assistance belongs in authoring and review, before the asset is committed.

Each failed step emits driver-specific evidence. Reports use a shared result shape so local runs and distributed agents remain interchangeable.

