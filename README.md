# Reliability Engine

**Deterministic safeguards and privacy-conscious monitoring for small-LLM agent runtimes.**

Reliability Engine is a model-independent support layer for Hermes Agent and similar tool-using assistants. It detects and contains selected mechanical failure modes without calling another LLM for every check.

Its first release focuses on structural tool-call validation, bounded recovery from repeated malformed calls, response-anomaly telemetry, and runtime metrics. It does not claim to prove that natural-language answers are true.

## Boundary with Evidence Engine

Reliability Engine and [Evidence Engine](https://github.com/oORaxaOo/Evidence-Engine) have separate responsibilities:

- **Reliability Engine:** generic runtime robustness — tool-call structure and complexity, repeated malformed calls, response anomaly signals, and aggregate model/runtime metrics.
- **Evidence Engine:** deterministic verification of approved software-development criteria — build/test/file evidence, evidence-chain integrity, and the coding verification gate.

Reliability Engine does not create coding tasks, collect build/test evidence, verify files or builds, or override Evidence Engine decisions. A future integration may read an Evidence Engine result, but it must remain read-only and preserve Evidence Engine as the authority for coding verification.

## Hermes compatibility

The native plugin targets Hermes Agent **v0.23.1 or newer** and uses its documented plugin contracts:

- `pre_tool_call` for structural validation and blocking malformed or oversized tool arguments;
- API and tool lifecycle hooks for metadata-only monitoring;
- `post_llm_call` for non-invasive response anomaly checks;
- a short, bounded system-prompt section with conservative operating guidance;
- `/reliability` for aggregate in-memory status.

It does not replace Hermes' memory provider, context engine, model provider, retry/failover logic, or tool schemas. It makes no auxiliary LLM calls and has no third-party Python runtime dependencies.

## Privacy

The initial monitor stores aggregate counters only. It does **not** retain prompts, conversation history, assistant responses, tool arguments, tool results, API request bodies, or raw exception messages. Metrics are process-local and reset when the plugin process restarts.

## Local tests

Python 3.11+; standard library only:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

See [architecture](docs/architecture.md), [configuration](docs/configuration.md), and [security](docs/security.md).
