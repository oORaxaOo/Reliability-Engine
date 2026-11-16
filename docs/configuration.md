# Configuration

Settings live under `plugins.entries.reliability-engine.settings` in Hermes'
existing `config.yaml`.

| Setting | Default | Allowed range | Purpose |
|---|---:|---:|---|
| `max_tool_args_bytes` | 32768 | 1024–1048576 | Maximum serialized tool-argument size |
| `max_tool_depth` | 12 | 2–32 | Maximum nested JSON depth |
| `max_tool_items` | 512 | 16–10000 | Maximum combined object/list members |
| `max_tool_string_chars` | 16384 | 256–262144 | Maximum individual string/key length |
| `max_invalid_tool_calls` | 3 | 1–10 | Consecutive malformed calls before session-level blocking |
| `max_response_chars` | 100000 | 1000–1000000 | Response length above which a mechanical anomaly is recorded |
| `context_budget_tokens` | 65536 | 0–1000000 | Configured context budget used for passive pressure telemetry; 0 disables it |
| `profile_model_label` | Gemma E4B Q4 Uncensored | 1–80 characters | Fallback display label when Hermes does not supply model metadata |
| `kie_database` | empty | absolute path | Optional KIE event ledger; publication is disabled when empty |

Invalid or out-of-range integer settings fall back to bounded defaults.
Values are clamped to the documented range.

Example:

```yaml
plugins:
  entries:
    reliability-engine:
      settings:
        max_tool_args_bytes: 32768
        max_tool_depth: 12
        max_tool_items: 512
        max_tool_string_chars: 16384
        max_invalid_tool_calls: 3
        max_response_chars: 100000
        context_budget_tokens: 65536
        profile_model_label: "Gemma E4B Q4 Uncensored"
        kie_database: /absolute/path/to/kie-integration.sqlite3
```

Preserve all unrelated existing keys in `config.yaml`.

## Optional KIE publication

When KIE is installed in the same Python environment and `kie_database` is
set to an absolute path, Reliability publishes one privacy-minimized aggregate
snapshot on `on_session_end`.

Only total counters, selected context/latency metrics, and allowlisted
mechanical anomaly counts are transferred. Model labels, tool names, exception
types/messages, prompts, responses, and tool arguments are excluded. The KIE
database remains owned by KIE; Reliability does not open its own database.

Publication is optional and fail-open. Missing KIE or a failed write cannot
block the Hermes session-end hook. Metrics remain process-local in Reliability
and are not made persistent by this integration.

Context pressure is measured against the configured budget: warning at 75%
and critical at 90%. These are status metrics only; the profiler does not send
repeated alerts, interrupt calls, truncate, summarize, or rewrite context.

The profiler stores aggregate counters only. It records model-turn counts and
an allowlist of technical signals. Task outcomes are never inferred from tone,
word choice, or response content; they are included only when explicitly
labelled with `/reliability label <category> <outcome>`. No profanity,
uncensored-language, opinion, or style scoring exists. All data is
process-local and resets when the plugin process restarts.
