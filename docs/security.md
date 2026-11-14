# Security and trust boundaries

- Tool-call validation is structural only. It is not a permission system, sandbox, command policy, or semantic safety classifier.
- Hermes tool schemas, guardrails, approval flows, and host permissions remain in force and remain authoritative.
- The plugin blocks malformed or over-limit argument payloads through `pre_tool_call`; it never rewrites tool arguments.
- Runtime metrics contain metadata only. Do not add prompts, assistant responses, tool arguments/results, credentials, or raw provider errors to the monitor.
- The system-prompt guidance is advisory and must not be treated as a security boundary.
- Hermes plugin hooks are opt-in and hook dispatch is exception-isolated. Operators must verify the plugin is enabled and healthy; this plugin cannot claim to protect sessions in which it is not loaded.
- The monitor and repeated-call guard are in-memory. A process restart clears them.
- The response inspector reports mechanical anomalies only. It does not establish factual correctness.
- Evidence Engine's verification state is out of scope. Reliability Engine must never turn an unverified coding result into a successful one.
