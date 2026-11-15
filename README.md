# Reliability Engine

**Deterministic safeguards and privacy-conscious monitoring for small-LLM agent runtimes.**

Reliability Engine is a model-independent support layer for Hermes Agent and similar tool-using assistants. The current deployment target is **Gemma E4B Q4 Uncensored**, with a configured 65,536-token context budget. It detects selected mechanical failure modes without calling another LLM for every check.

Its core includes structural tool-call validation, bounded recovery from repeated malformed calls, response-anomaly telemetry, runtime metrics, and a passive Model Behavior Profiler. It does not claim to prove that natural-language answers are true.

## Boundary with Evidence Engine

Reliability Engine and [Evidence Engine](https://github.com/oORaxaOo/Evidence-Engine) have separate responsibilities:

- **Reliability Engine:** generic runtime robustness — tool-call structure and complexity, repeated malformed calls, mechanical response anomalies, and aggregate model/runtime behavior metrics.
- **Evidence Engine:** deterministic verification of approved software-development criteria — build/test/file evidence, evidence-chain integrity, and the coding verification gate.

Reliability Engine does not create coding tasks, collect build/test evidence, verify files or builds, or override Evidence Engine decisions. A future integration may read an Evidence Engine result, but it must remain read-only and preserve Evidence Engine as the authority for coding verification.

## Hermes compatibility

The native plugin targets Hermes Agent **v0.23.1 or newer** and uses its documented plugin contracts:

- `pre_tool_call` for structural validation and blocking malformed or oversized tool arguments;
- API and tool lifecycle hooks for metadata-only monitoring;
- `post_llm_call` for non-invasive response anomaly checks and model-turn counts;
- a short, bounded system-prompt section with conservative operating guidance;
- `/reliability` for aggregate in-memory status and profiling.

It does not replace Hermes' memory provider, context engine, model provider, retry/failover logic, or tool schemas. It makes no auxiliary LLM calls and has no third-party Python runtime dependencies.

## Model Behavior Profiler

The profiler is deliberately passive. It records counts for model turns, a fixed allowlist of technical signals, and task outcomes that the user explicitly labels.

- `/reliability profile` displays the profile.
- `/reliability label research success` adds an explicit user rating. Categories: `conversation`, `research`, `coding`, `file_ops`, `automation`, `tool_use`, `other`. Outcomes: `success`, `partial`, `failure`, `unverified`.

It does **not** infer task success from an LLM response, inspect prompts or response text for profanity, score tone/opinions, or trigger automatic alerts. The word **Uncensored** in the model label is metadata only. No content is stored; aggregate counters remain in memory and reset when the plugin process restarts.

## First-release behavior

- Structural tool arguments are checked before execution. Invalid or over-limit calls are blocked with a short correction message.
- After repeated consecutive malformed calls in one session, further malformed calls are blocked until a valid call or turn/session completion clears the guard.
- Final responses are inspected for mechanical anomalies only; they are never silently rewritten.
- Main and auxiliary provider requests are counted. Latencies for provider calls and tool-call events are measured separately.
- Context pressure is passively reported against the configured budget: warning at 75%, critical at 90%. Transition counters increment only when changing bands. The plugin never modifies context.
- `/reliability` reports aggregate process-local metrics.

## Privacy

The monitor and profiler store aggregate counters only. They do **not** retain prompts, conversation history, assistant responses, tool arguments, tool results, API request bodies, or raw exception messages. Metrics are process-local and reset when the plugin process restarts.

## Install as a Hermes plugin

The plugin is opt-in. Install it into the intended Hermes profile only after reviewing the current default-branch code:

```bash
hermes plugins install oORaxaOo/Reliability-Engine
hermes plugins enable reliability-engine
hermes plugins doctor reliability-engine
```

Merge optional settings into the existing `~/.hermes/config.yaml`:

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

Do not replace the rest of your Hermes configuration. The plugin requires Hermes Agent v0.23.1 or newer.

## Local tests

Python 3.11+; standard library only:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

See [architecture](docs/architecture.md), [configuration](docs/configuration.md), and [security](docs/security.md).
