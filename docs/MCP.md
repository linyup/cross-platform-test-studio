# MCP integration

The optional MCP server lets Codex and other agents explore desktop and mobile interfaces without coupling agent policy to a platform driver.

## Boundaries

- Skills decide the workflow, evidence order, review gate and promotion policy.
- MCP translates structured tool calls into the shared Driver and `ExplorationSession` contracts.
- Drivers own Playwright/CDP, ADB, WDA or simulation details.
- Committed Flow regression uses `FlowRunner` directly and never depends on MCP or an LLM.
- Remote device scheduling, authentication and tenancy stay in the Device Lab HTTP API.

## Lifecycle

1. Check `test_get_status`.
2. Inspect with `test_inspect`; use `test_snapshot` only when image evidence is needed.
3. Preserve the returned page fingerprint and use `test_compare_state` before acting on stale observations.
4. Create one trace per scenario.
5. Use `test_run_journey` for known paths and `test_perform` for uncertain steps.
6. Review the trace and discard provisional mistakes.
7. Complete the trace, compile a draft, and pass it through the human review and Cleanup gate.
8. Promote the reviewed draft; run committed Flows deterministically.

The server is process-local by design. Trace state is ephemeral until a draft is compiled and saved by the caller. Production deployments should use `stdio` locally or put authenticated network transport behind an internal gateway.

## Tool groups

- Observation: `test_get_status`, `test_inspect`, `test_snapshot`, `test_compare_state`
- Action: `test_perform`, `test_assert`, `test_run_journey`
- Trace: `test_create_trace`, `test_get_trace`, `test_discard_trace_step`, `test_complete_trace`
- Promotion: `test_compile_flow_draft`

`test_inspect` already returns the usable element collection, so a duplicate `get_elements` tool is unnecessary. `test_perform` records into the trace atomically, so a separate `record_action` call cannot drift away from the actual device action.
