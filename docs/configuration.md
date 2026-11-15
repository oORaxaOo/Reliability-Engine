# Configuration

Settings live under `plugins.entries.reliability-engine.settings` in Hermes' existing `config.yaml`.

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

Invalid or out-of-range integer settings fall back to bounded defaults. Values are clamped to the documented range.

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
```

Preserve all unrelated existing keys in `config.yaml`.

Context pressure is measured against the configured budget: warning at 75% (49,152 tokens) and critical at 90% (about 58,982 tokens) for a 65,536-token budget. The monitor counts transitions between bands, not every API request spent in the same band. These are status metrics only; the profiler does not send repeated alerts, interrupt calls, truncate, summarize, or rewrite context. Hermes' input-token figure is an estimate, not a guarantee of exact model token usage.

The profiler stores aggregate counters only. It records model-turn counts and an allowlist of technical signals. Task outcomes are never inferred from tone, word choice, or response content; they are included only when explicitly labelled with `/reliability label <category> <outcome>`. No profanity, uncensored-language, opinion, or style scoring exists. All data is process-local and resets when the plugin process restarts.
