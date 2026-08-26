# Containing Frontier Cyber Agents

**Working title:** Containing Frontier Cyber Agents: An Empirical Evaluation
of Defense-in-Depth Controls Against Autonomous AI Attack Chains

This repository implements a defensive, synthetic research instrument. All
experiments are intended to remain inside an isolated laboratory safety
boundary. The project does not target real systems or seek to improve offensive
capability.

The scientific design was frozen before executable implementation began. The
current implementation stage provides only repository scaffolding and a strict
JSON Schema validation foundation; it contains no scientific contract-family
schemas or experimental infrastructure. No experimental findings exist yet.

## Frozen governing artifacts

| File | Tag |
| --- | --- |
| `docs/research-contract-v0.1.md` | `research-contract-v0.1` |
| `docs/threat-scenario-spec-v0.1.md` | `threat-scenario-spec-v0.1` |
| `docs/control-architecture-spec-v0.1.md` | `control-architecture-spec-v0.1` |
| `docs/evidence-spec-v0.1.md` | `evidence-spec-v0.1` |
| `docs/instrument-validation-spec-v0.1.md` | `instrument-validation-spec-v0.1` |
| `docs/statistical-analysis-plan-v0.1.md` | `statistical-analysis-plan-v0.1` |
| `docs/implementation-contract-v0.1.md` | `implementation-contract-v0.1` |

## Schema technology

Executable contracts will use JSON Schema Draft 2020-12. It provides a mature,
well-supported vocabulary for strict machine-readable research contracts,
including modern `$defs` and reference semantics. Python's `jsonschema`
implementation provides direct `Draft202012Validator` support.

This foundation is not a claim that the research instrument is validated,
secure, complete, or production-ready.
