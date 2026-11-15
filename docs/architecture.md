# Architecture

## Design goals

1. Improve reliability around small language models using deterministic code before considering additional inference.
2. Keep the runtime plugin independent from the model and reusable outside Hermes.
3. Preserve Hermes as the authority for tool registration, permissions, approvals, execution, and provider retry/failover.
4. Keep Evidence Engine focused on verifiable software-development outcomes.
5. Avoid retaining private conversation or tool content.

## Runtime flow

```text
User turn
   |
   v
Hermes context + model request
   |                 \
   |                  +--> pre_api_request / post_api_request / api_request_error
   |                       (counts, latency, estimated input size, error category)
   v
Model-generated tool call
   |
   v
Hermes tool schema / normal pre-execution path
   |
   v
Reliability Engine: pre_tool_call
   |-- invalid structure/size/depth --> block with bounded corrective feedback
   |-- valid ------------------------> continue into Hermes guardrails/approval/tool
   |
   v
Tool result --> post_tool_call metadata only
   |
   v
Final response --> post_llm_call anomaly inspection --> normal delivery
```

## Components

### ToolCallValidator

A pure-Python validator checks JSON compatibility and conservative complexity bounds. It intentionally does not duplicate tool-specific JSON schemas and does not judge whether a command, search, or other action is appropriate. Hermes' own schema and approval mechanisms remain authoritative.

### Invalid-call guard

A consecutive invalid-call counter is maintained per session. Once the configured limit is reached, further structurally invalid calls are blocked with a stop-and-clarify message. A valid call or completed turn clears the guard. The guard is bounded in memory.

### Response inspector

The inspector flags only mechanical patterns: non-text/empty result, excessive length, and repeated long lines. It does not rewrite responses, infer truth, or call another model.

### Runtime monitor

The monitor stores only aggregate counters and bounded rolling samples for API latency and estimated input size. If an operator explicitly configures the effective context budget, it classifies the latest estimated input size as normal, warning (75%), or critical (90%). This is telemetry, not an exact measurement or context manager. It deliberately discards prompt text, model output, tool arguments, tool results, and raw error messages.

### Hermes plugin adapter

`plugin.py` wires the reusable core to hooks available in Hermes Agent v0.23.1. The adapter is thin; validation and metrics can be tested without importing Hermes.

## Why no custom LLM retry loop?

Hermes already owns provider retry and failover. Replaying model or tool calls from another plugin could duplicate side effects, conflict with Hermes' retry accounting, or create loops. This release observes provider failures and bounds repeated malformed tool calls, but does not implement a second LLM retry system.

## Why no custom context engine?

Replacing Hermes' context engine would be invasive and may conflict with installed memory/context plugins. This release adds a short system-prompt guidance section and observes Hermes' approximate input-token metric. It does not truncate or rewrite conversation history. A later context module must be opt-in and tested against the user's configured Hermes context engine.

## Evidence Engine boundary

Evidence Engine remains the system of record for software task contracts and verification. Reliability Engine may eventually consume a read-only verification report, but it must not write evidence, define coding success criteria, run builds/tests, or alter an Evidence Engine result.

## Current model target: Gemma E4B Q4

The current target model label supplied by the operator is **Gemma E4B Q4**. The plugin does not assume a particular Gemma generation, provider wrapper, quantization implementation, or context limit from that label. The context budget remains disabled until the exact model variant and effective Hermes provider context setting are confirmed. Tool validation and runtime telemetry remain model-independent.
