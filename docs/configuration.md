# Configuration

Settings live under `plugins.entries.reliability-engine.settings` in Hermes' existing `config.yaml`.

| Setting | Default | Allowed range | Purpose |
|---|---:|---:|---|
| `max_tool_args_bytes` | 32768 | 1024–1048576 | Maximum serialized tool-argument size |
| `max_tool_depth` | 12 | 2–32 | Maximum nested JSON depth |
| `max_tool_items` | 512 | 16–10000 | Maximum combined object/list members |
| `max_tool_string_chars` | 16384 | 256–262144 | Maximum individual string/key length |
| `max_invalid_tool_calls` | 3 | 1–10 | Consecutive malformed calls before session-level blocking |
| `max_response_chars` | 100000 | 1000–1000000 | Response length above which an anomaly is recorded |
| `context_budget_tokens` | 0 (disabled) | 0–1000000 | Explicit context-window budget used for pressure warnings; set only to the actual configured budget |

Invalid or out-of-range settings fall back to bounded defaults. Values are clamped to the documented range.

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
        context_budget_tokens: 0
```

Preserve all unrelated existing keys in `config.yaml`.


Context pressure is measured against the explicitly configured budget: warning at 75%, critical at 90%. A value of `0` disables pressure classification. Hermes' input-token figure is an estimate, not a guarantee of exact model token usage. Reliability Engine never truncates, summarizes, or rewrites context.

For the current target **Gemma E4B Q4**, leave this setting disabled until the exact model variant and effective context limit in the Hermes provider configuration have been confirmed. Do not infer the context budget from the quantization label.
