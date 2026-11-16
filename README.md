# Reliability Engine

**Deterministic safeguards and privacy-conscious monitoring for small-LLM agent runtimes.**

Reliability Engine is a model-independent support layer for Hermes Agent and
similar tool-using assistants. It detects selected mechanical failure modes
without calling another LLM for every check.

Its core includes structural tool-call validation, bounded recovery from
repeated malformed calls, response-anomaly telemetry, runtime metrics, and a
passive Model Behavior Profiler. It does not claim to prove that
natural-language answers are true.

## Boundary with Evidence Engine

Reliability Engine and [Evidence Engine](https://github.com/oORaxaOo/Evidence-Engine)
have separate responsibilities:

- **Reliability Engine:** generic runtime robustness — tool-call structure and
  complexity, repeated malformed calls, mechanical response anomalies, and
  aggregate model/runtime behavior metrics.
- **Evidence Engine:** deterministic verification of approved
  software-development criteria — build/test/file evidence, evidence-chain
  integrity, and the coding verification gate.

Reliability Engine does not create coding tasks, collect build/test evidence,
verify files or builds, or override Evidence Engine decisions.

## Optional KIE publication

When configured with the shared absolute `kie_database` path, Reliability
publishes a bounded aggregate snapshot at session end through
`kie.publisher`. The snapshot excludes model labels, tool names, exception
details, prompts, responses, and tool arguments. It remains an optional,
fail-open integration and does not alter Reliability's in-memory metrics or
privacy model.

## Hermes compatibility

The native plugin targets Hermes Agent **v0.23.1 or newer** and uses its
documented plugin contracts:

- `pre_tool_call` for structural validation and blocking malformed or
  oversized tool arguments;
- API and tool lifecycle hooks for metadata-only monitoring;
- `post_llm_call` for non-invasive response anomaly checks and model-turn
  counts;
- a short, bounded system-prompt section with conservative operating guidance;
- `/reliability` for aggregate in-memory status and profiling.

It does not replace Hermes' memory provider, context engine, model provider,
retry/failover logic, or tool schemas. It makes no auxiliary LLM calls and has
no third-party Python runtime dependencies.

## Model Behavior Profiler

The profiler is deliberately passive. It records counts for a fixed allowlist
of technical signals, and task outcomes that the user explicitly labels.
It does not infer task success from an LLM response, inspect prompts or
response text for profanity, score tone/opinions, or trigger automatic alerts.

## Privacy

The monitor and profiler store aggregate counters only. They do not retain
prompts, conversation history, assistant responses, tool arguments, tool
results, API request bodies, or raw exception messages. Metrics are
process-local and reset when the plugin process restarts.

## Local tests

Python 3.11+; standard library only:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

See [architecture](docs/architecture.md), [configuration](docs/configuration.md),
and [security](docs/security.md).
