# Schema foundation

Executable contracts in this repository will use JSON Schema Draft 2020-12.
This directory will contain version-controlled executable contracts, but Stage
1 intentionally contains no scientific contract-family schemas. Stage 2 will
establish shared identifier, version, lifecycle, and enumeration semantics.

Every future schema must preserve the semantics of the frozen design documents.
Strict validation is preferred: the project validator performs no type
coercion, repair, migration, or input rewriting. Schemas should reject unknown
critical fields where appropriate and distinguish required, optional, and
explicitly missing states according to the governing contracts.

Remote or external schema resolution must not become an uncontrolled network
dependency. The Stage 1 validator accepts only references within the supplied
schema document; cross-contract reference resolution is deferred. A standard
Draft 2020-12 `$schema` URI identifies the dialect without requiring network
retrieval because validation uses the installed `jsonschema` implementation.

## Traceability

This foundation derives from the frozen
`docs/implementation-contract-v0.1.md`, especially:

- Section 5, **Executable Contract Families**;
- Section 21, **Cross-Contract Referential Integrity**;
- Section 22, **Enumeration Ownership**;
- Section 23, **Schema Strictness Principles**;
- Section 35, **Test Requirements for Executable Contracts**; and
- Section 36, **Minimum Viable Implementation Order**.

Stage 1 supplies only the validation foundation required by that order. It does
not implement the contract families, referential-integrity rules, or canonical
enumerations governed by those sections.
