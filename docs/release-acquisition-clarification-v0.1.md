# Release Acquisition Clarification v0.1

## 1. Status and authority

This design clarification supplements the frozen Release Integrity Profile
v0.1 and its governing integrity and reproducibility contracts. It resolves
the deterministic acquisition details required before Stage 12E-2 can be
implemented. It does not replace, weaken, or reinterpret any scientific,
artifact, manifest, integrity, or claims boundary.

This document authorizes no source or schema change, package installation,
release assembly, Git tag creation, scientific execution, or security-boundary
work. Stage 12E-2 implementation requires separate approval after this
clarification is reviewed and frozen.

## 2. Purpose

This clarification freezes v0.1 acquisition semantics for:

1. `os_release_identity`;
2. `libc_identity`;
3. `locale_identity`;
4. `timezone_identity`;
5. the PEP 405 virtual-environment backend;
6. system-site and user-site acquisition;
7. requirement-parsing tooling and dependency edges; and
8. the public machine-readable projection of the governing-document registry.

All acquired values remain bounded local observations. They are not claims of
authenticity, scientific validity, hermeticity, containment, or security.

## 3. Linux OS-release backend

For Linux v0.1 acquisition, Stage 12E-2 obtains operating-system release
metadata from the freedesktop `os-release` mechanism using this exact source
precedence:

1. `/etc/os-release`; then
2. only when `/etc/os-release` does not exist, `/usr/lib/os-release`.

The two files MUST NOT be merged. `PRETTY_NAME` is not a normative identity
source.

The selected file is parsed according to `os-release` assignment and quoting
syntax. Interpreting that file format, including its quoted-value syntax, is
syntax parsing rather than identity normalization. The parser MUST NOT execute
the file as shell code. A malformed record or an ambiguous duplicate of a
required field causes acquisition to fail.

## 4. OS-release required fields

The selected `os-release` file MUST contain nonempty parsed values for both:

```text
ID
VERSION_ID
```

Each exact parsed value MUST independently match:

```text
[A-Za-z0-9][A-Za-z0-9._-]*
```

An absent, empty, malformed, or unrepresentable value causes acquisition to
fail. V0.1 defines no fallback to `PRETTY_NAME`, `VERSION`,
`VERSION_CODENAME`, or `ID_LIKE`.

## 5. OS-release identity serialization

Stage 12E-2 constructs:

```text
os_release_identity = <ID> + "-" + <VERSION_ID>
```

Both components are the exact parsed values. Acquisition MUST NOT change case,
add marketing text, codename, `LTS`, or patch data from another field, replace
characters, or normalize punctuation.

For the current non-normative observation:

```text
ID=ubuntu
VERSION_ID=24.04
```

the result is exactly:

```text
ubuntu-24.04
```

The earlier `Ubuntu-24.04.3-LTS` text was illustrative and is superseded as an
acquisition example by this exact v0.1 rule.

## 6. OS-release test requirements

Stage 12E-2 tests MUST include at least:

| Input | Expected result |
| --- | --- |
| `ID=ubuntu`, `VERSION_ID=24.04` | `ubuntu-24.04` |
| `ID=example`, `VERSION_ID=1.2.3` | `example-1.2.3` |
| missing `ID` | failure |
| missing `VERSION_ID` | failure |
| whitespace in `ID` | failure |
| slash in `VERSION_ID` | failure |
| only `PRETTY_NAME` present | failure |

No test may satisfy an invalid case through coercion.

## 7. libc acquisition and serialization

Stage 12E v0.1 acquires libc identity through the explicitly selected Python
interpreter using:

```text
platform.libc_ver()
```

The returned pair is interpreted as `(implementation, version)`. Both values
MUST be nonempty and MUST independently match:

```text
[A-Za-z0-9][A-Za-z0-9._-]*
```

The identity is constructed exactly as:

```text
libc_identity = <implementation> + "-" + <version>
```

For the current non-normative observation `("glibc", "2.39")`, the result is
`glibc-2.39`.

No case conversion, punctuation replacement, or shell-output parsing is
permitted.

## 8. libc failure and fallback

V0.1 defines no fallback backend for libc acquisition. Stage 12E-2 MUST NOT
automatically invoke `ldd --version`, `getconf`, package-manager queries, or
filesystem heuristics.

If `platform.libc_ver()` returns an empty implementation or version, or either
exact value is not schema-representable, acquisition fails. A later profile
version may define a separate backend explicitly.

## 9. Locale purpose and categories

`Release Build Record.locale_identity` represents the effective locale
configuration selected for the research runtime. Because the v0.1 field is a
scalar, acquisition MUST NOT compress a mixed multi-category locale
configuration into one misleading identity.

The relevant POSIX locale categories are:

```text
LC_COLLATE
LC_CTYPE
LC_MESSAGES
LC_MONETARY
LC_NUMERIC
LC_TIME
```

Stage 12E-2 reads the selected runtime process environment exactly. PID, shell
display formatting, and `locale` command output are not identity sources.

## 10. Locale precedence

Stage 12E-2 uses this exact algorithm:

1. If `LC_ALL` exists and is nonempty, `locale_identity` is the exact
   `LC_ALL` value. No other locale environment variable participates.
2. Otherwise, `LANG` MUST exist and be nonempty.
3. For each of the six categories, the effective value is the exact nonempty
   category-specific environment value when present, otherwise the exact
   `LANG` value.
4. If all six effective values are exactly identical, `locale_identity` is
   that common value.
5. If the effective values differ, acquisition fails.

No scalar aggregation is defined in v0.1.

## 11. Locale representability and observation

The selected exact `locale_identity` MUST satisfy the frozen Release Build
Record schema. Stage 12E-2 MUST NOT change case, canonicalize aliases, alter
underscore or hyphen usage, map `C.UTF-8` to `C.utf8`, or invoke locale alias
normalization. An unrepresentable exact identity causes acquisition failure.

The current environment was observed non-normatively as:

```text
LC_ALL=C.UTF-8
LC_CTYPE=C.UTF-8
LANG=en_US.UTF-8
```

Under the precedence above, the result is `C.UTF-8` because the explicit
nonempty `LC_ALL` value has authority.

## 12. Locale test requirements

Future fixed tests MUST cover:

| Environment | Expected result |
| --- | --- |
| `LC_ALL=C.UTF-8`, `LANG=en_US.UTF-8` | `C.UTF-8` |
| `LC_ALL` absent, `LANG=en_US.UTF-8`, no overrides | `en_US.UTF-8` |
| `LC_ALL` absent, `LANG=en_US.UTF-8`, `LC_CTYPE=en_US.UTF-8` | `en_US.UTF-8` |
| `LC_ALL` absent, `LANG=en_US.UTF-8`, `LC_TIME=C.UTF-8` | failure |
| neither `LC_ALL` nor `LANG` supplies a value | failure |

## 13. Timezone purpose

`timezone_identity` is the stable timezone identity used by the selected
runtime. Stage 12E-2 prefers an IANA key such as `UTC` or
`America/New_York`. Abbreviations such as `EST`, `EDT`, or `CST` are not
normative identities when an IANA identity can be acquired.

## 14. Timezone source precedence

V0.1 uses this exact precedence:

1. an explicit nonempty `TZ` process-environment value;
2. an `/etc/localtime` IANA symlink identity; then
3. an `/etc/timezone` identity subject to the consistency and byte-comparison
   rules below.

`time.tzname` is not a normative identity source.

## 15. Explicit TZ override

When `TZ` is present and nonempty, its exact value is the timezone candidate.
The candidate MUST:

- not be an absolute path;
- not begin with the POSIX path prefix `:`; and
- load successfully through Python's `zoneinfo.ZoneInfo`.

If valid, `timezone_identity` is the exact `TZ` value. The explicit process
override may intentionally differ from host configuration, so it is not
compared with `/etc/timezone` or `/etc/localtime`. Invalid, path-like, or
unresolvable values cause acquisition failure.

## 16. `/etc/localtime` symlink

When `TZ` is absent or empty, Stage 12E-2 inspects `/etc/localtime`. If it is a
symbolic link whose resolved target is beneath `/usr/share/zoneinfo/`, the
candidate is the exact relative path below that root.

For example:

```text
/usr/share/zoneinfo/America/New_York
```

produces `America/New_York`. The candidate MUST load through
`zoneinfo.ZoneInfo`. Aliases are not normalized.

## 17. `/etc/timezone` parsing

When `/etc/timezone` exists, Stage 12E-2 parses it as one timezone-identity
line. Parsing may remove only:

- the terminating CR/LF line ending; and
- leading or trailing ASCII horizontal whitespace.

The result MUST be nonempty, contain no embedded line break, and load through
`zoneinfo.ZoneInfo`. These are explicit configuration-file syntax rules, not
general identity normalization.

## 18. Timezone consistency and regular-localtime fallback

When `TZ` is absent and both a symlink-derived `/etc/localtime` identity and a
valid `/etc/timezone` identity are available, they MUST be exactly equal. A
mismatch causes acquisition failure; neither source silently wins.

If `/etc/localtime` is not a usable zoneinfo symlink but `/etc/timezone`
provides a valid identity, Stage 12E-2 may use that identity only when the
exact bytes of `/etc/localtime` equal the exact bytes of:

```text
/usr/share/zoneinfo/<timezone_identity>
```

If byte equality cannot be established, acquisition fails. V0.1 defines no
fallback from a timezone abbreviation, numeric UTC offset, datetime display,
or host marketing name.

## 19. Timezone observation and tests

The current environment was observed non-normatively as:

```text
TZ unset
/etc/timezone = America/New_York
/etc/localtime -> /usr/share/zoneinfo/America/New_York
Python abbreviation = EDT
```

The exact v0.1 result is `America/New_York`.

Future fixed tests MUST cover a valid explicit IANA `TZ` override; invalid and
path-like `TZ`; localtime symlink alone; matching and mismatching localtime plus
`/etc/timezone`; regular localtime with matching and mismatching zonefile
bytes; and abbreviation-only failure.

## 20. PEP 405-only runtime backend

Stage 12E v0.1 Release Build Record acquisition supports only PEP 405 virtual
environments. The explicitly selected interpreter MUST satisfy:

```text
sys.prefix != sys.base_prefix
```

and MUST have a corresponding readable `pyvenv.cfg` at the environment root.
If either condition fails, acquisition fails. Stage 12E-2 MUST NOT silently
switch to a system-Python backend.

A non-venv interpreter is unsupported in v0.1 and cannot be classified as
`CONTROLLED_RUNTIME`. A later profile version may define another backend.

## 21. System-site acquisition

For the PEP 405 backend, the authoritative source for
`system_site_packages_enabled` is `include-system-site-packages` in
`pyvenv.cfg`.

The parser accepts only explicit case-insensitive boolean values corresponding
to `true` and `false`. A missing, malformed, or ambiguously duplicated key
causes acquisition failure. The value MUST NOT be inferred from `sys.path` or
from whether a particular system package imports successfully.

## 22. User-site acquisition

User-site state is acquired by a probe executed through the explicitly
selected interpreter. Stage 12E-2 reads:

```text
site.ENABLE_USER_SITE
sys.flags.no_user_site
```

The acquired `user_site_packages_enabled` value is true if and only if
`site.ENABLE_USER_SITE is True`. `False` and `None` both produce false,
provided the runtime state is not contradictory.

If `sys.flags.no_user_site == 1`, `site.ENABLE_USER_SITE` MUST NOT be true. A
contradiction causes acquisition failure. Directory existence alone does not
establish enablement.

## 23. Environment mode consistency

Stage 12E-2 does not infer a scientific release phase or Environment Contract
from site flags. The caller supplies the requested `environment_mode`, which
MUST be either:

```text
DEVELOPMENT_TOOLING
CONTROLLED_RUNTIME
```

For `CONTROLLED_RUNTIME`, both acquired site-package flags MUST be false. If
either is true, acquisition fails. `DEVELOPMENT_TOOLING` permits either value.
False flags alone do not prove controlled-runtime completeness, hermeticity, or
security.

The current `.venv` observation is:

```text
include-system-site-packages = true
site.ENABLE_USER_SITE = true
sys.flags.no_user_site = 0
```

It remains `DEVELOPMENT_TOOLING` and cannot satisfy `CONTROLLED_RUNTIME`.

## 24. Requirement-parser tooling

Stage 12E dependency closure requires standards-compliant parsing of PEP 508
requirements, PEP 440 versions and specifiers, and environment markers. Stage
12E MUST NOT implement an ad hoc parser.

The acquisition parser is:

```text
packaging==24.0
```

The currently observed `packaging 24.0` installation is inherited and
undeclared. That observation is insufficient for a frozen acquisition
implementation.

## 25. Declared release-integrity tooling extra

A later approved Stage 12E-2 implementation is authorized to add this exact
optional project tooling extra:

```toml
[project.optional-dependencies]
release-integrity = [
    "packaging==24.0",
]
```

It MUST preserve the existing `test` extra and MUST NOT add `packaging` to
`project.dependencies` solely for acquisition tooling. No installation or
network access is authorized by this clarification.

The Stage 12E acquisition tooling environment MUST load exactly
`packaging==24.0`; absence or a different loaded version causes the tooling to
fail closed.

## 26. Tooling and scientific-runtime separation

The `release-integrity` extra is acquisition and audit tooling. It is not
automatically part of the scientific `FULL_TRANSITIVE_RUNTIME` dependency
closure and MUST NOT be implicitly activated while resolving that closure.

Scientific closure begins from `project.dependencies` plus only scientific
runtime extras explicitly selected by the Release Profile. If `packaging`
becomes reachable independently from those scientific roots, it is included
normally.

## 27. Public governing-document registry projection

The Markdown Release Integrity Profile remains the normative source of the
nine-entry governing-document registry. Operational code MUST NOT parse the
Markdown.

Stage 12E implementation is authorized to expose exactly one explicit,
immutable, public machine-readable projection. Its preferred shape is:

```text
@dataclass(frozen=True, slots=True)
class GoverningDocumentRegistryEntry:
    document_id: str
    document_version: str
    repository_path: str
    frozen_tag_identity: str

GOVERNING_DOCUMENT_REGISTRY_V0_1: tuple[GoverningDocumentRegistryEntry, ...]
```

Exact public names may follow established project conventions. The projection
implements the frozen registry; it does not authorize another registry,
additional entries, inferred paths, or a hidden mapping elsewhere.

## 28. Exact public registry contents

The immutable tuple contains exactly these records in this order:

| `document_id` | `document_version` | `repository_path` | `frozen_tag_identity` |
| --- | --- | --- | --- |
| `research-contract` | `v0.1` | `docs/research-contract-v0.1.md` | `research-contract-v0.1` |
| `threat-scenario-spec` | `v0.1` | `docs/threat-scenario-spec-v0.1.md` | `threat-scenario-spec-v0.1` |
| `control-architecture-spec` | `v0.1` | `docs/control-architecture-spec-v0.1.md` | `control-architecture-spec-v0.1` |
| `evidence-spec` | `v0.1` | `docs/evidence-spec-v0.1.md` | `evidence-spec-v0.1` |
| `instrument-validation-spec` | `v0.1` | `docs/instrument-validation-spec-v0.1.md` | `instrument-validation-spec-v0.1` |
| `statistical-analysis-plan` | `v0.1` | `docs/statistical-analysis-plan-v0.1.md` | `statistical-analysis-plan-v0.1` |
| `implementation-contract` | `v0.1` | `docs/implementation-contract-v0.1.md` | `implementation-contract-v0.1` |
| `integrity-reproducibility-spec` | `v0.1` | `docs/integrity-reproducibility-spec-v0.1.md` | `integrity-reproducibility-spec-v0.1` |
| `integrity-reproducibility-clarification` | `v0.1` | `docs/integrity-reproducibility-clarification-v0.1.md` | `integrity-reproducibility-clarification-v0.1` |

There is no tenth entry and no inferred path.

## 29. Registry verification boundary

Tests for the public projection MUST establish:

- exactly nine entries;
- exact tuple order and content;
- frozen entry values and immutable tuple storage;
- no duplicate `document_id`;
- exact correspondence with the frozen profile; and
- existence of each registered path at its registered historical tag.

No hidden second registry may exist elsewhere.

## 30. Governing acquisition and source-copy consistency

Stage 12E-2 receives `source_release_tag_identity` explicitly. For every
public registry entry, it acquires:

Historical frozen facts:

- annotated historical tag object identity;
- historical tag target commit; and
- exact bytes at `<historical-tag>:<repository_path>`.

Source release facts:

- exact bytes at `<source-release-tag>:<repository_path>`.

The exact source-release bytes MUST equal the exact historical-tag bytes. A
difference causes release provenance acquisition or audit to fail. No source
copy can be verified until an actual Source Release Tag exists.

The document digest remains an exact-byte document content digest:

```text
SHA-256(exact document bytes)
```

There is no JCS, decoding, re-encoding, or normalization. A governing document
is neither a forensic input nor a canonical JSON artifact.

## 31. Dependency identity and conflict rule

The scientific dependency identity supplied to Stage 12D is the exact
distribution `Name` from authoritative installed METADATA. Stage 12E performs
no undocumented case or punctuation normalization of that emitted identity.

Within the acquired transitive runtime closure:

- an identical exact METADATA Name and exact version collapses to one semantic
  dependency; and
- one exact METADATA Name with distinct exact versions causes acquisition to
  fail.

Stage 12E MUST NOT choose a dependency through `sys.path` precedence, highest
version, or first-result ordering.

## 32. Dependency edge and version rule

Every installed dependency MUST satisfy every applicable incoming PEP 440
specifier using `packaging==24.0` semantics. An unsatisfied edge or missing
required distribution causes acquisition to fail. Stage 12E-2 does not install
a compatible substitute.

Environment markers are evaluated for the explicitly selected runtime. Cycles
are handled deterministically through traversal state and do not truncate
closure. Closure output ordering MUST be deterministic.

## 33. Scientific runtime extras

Scientific runtime extras are enabled only by
`Release Profile.enabled_dependency_extras`. Stage 12E-2 MUST verify that every
requested runtime extra is declared by the source-release project metadata.
An unknown requested extra causes acquisition failure; it is not silently
ignored.

The tooling-only `release-integrity` extra is not implicitly a scientific
runtime extra.

## 34. Distribution provenance boundary

For each resolved dependency, Stage 12E-2 reports
`distribution_filename` and `distribution_digest` only when locally
trustworthy original-distribution evidence exists.

Acceptable evidence includes a direct installation record whose archive hash
binds the installation to the original distribution artifact and, when the
artifact remains present, an independent exact-byte rehash. Installed package
directory digests, aggregate `RECORD` digests, and import-file digests MUST NOT
be promoted to original distribution provenance.

Acquisition reports availability and never fabricates a missing digest. Stage
12E-3 assembly and Stage 12E-4 audit enforce the phase rule that every PILOT or
CONFIRMATORY scientific runtime dependency has original-distribution digest
provenance. Stage 12E-2 does not enforce that phase completeness policy.

## 35. Release/build/tag equality boundary

Stage 12E-2 does not assemble `release_id`, `build_id`, or the source tag and
does not own their full cross-value equality gate.

Stage 12E-3 MUST enforce that:

```text
release:<phase>-vX.Y
build:<phase>-vX.Y
research-release-<phase>-vX.Y
release_phase
```

encode the same phase and release version. Stage 12E-4 independently rechecks
the relationship.

## 36. OS aggregate equality

Stage 12E-2 constructs `os_runtime_identity` from acquired component fields
exactly as:

```text
"system-" + os_system
+ "+release-" + os_release_identity
+ "+kernel-" + kernel_release
+ "+libc-" + libc_identity
```

No normalization occurs. Stage 12E-4 independently verifies exact equality
between this construction and the Release Build Record field. This resolves
the Stage 12E-1 deferred aggregate/component rule.

For the current non-normative observations, the result is:

```text
system-Linux+release-ubuntu-24.04+kernel-6.17.0-35-generic+libc-glibc-2.39
```

## 37. Fail-closed acquisition model

Stage 12E-2 fails closed when any required fact is unavailable, malformed,
ambiguous, contradictory, or not exactly schema-representable. It MUST NOT
substitute a placeholder, guess, empty-but-accepted value, fabricated
identity, or silently normalized value.

An acquisition error is returned as an explicit deterministic finding or
exception. A failed acquisition MUST NOT be converted into a valid Release
Build Record.

## 38. Claims boundary

These rules establish only deterministic local metadata acquisition, explicit
source precedence, exact local observation, controlled serialization, and
fail-closed representability checks.

They do not establish OS metadata authenticity, Git authenticity, package or
publisher authenticity, package integrity without trusted artifact evidence,
environment hermeticity, scientific evidence truth, containment
effectiveness, system security, or certification.

## 39. GREEN / RED boundary

Stage 12E-2 remains GREEN. Later approved acquisition may use read-only Git,
local configuration-file inspection, explicitly selected interpreter probes,
`importlib.metadata`, `packaging` requirement and marker parsing, and
deterministic SHA-256.

It MUST NOT execute a model or agent, attack chain, S0 or M3 runtime,
network-containment test, instrument-validation runtime, PILOT, or
CONFIRMATORY experiment. The previously frozen RED boundary remains
unchanged.

## 40. Compatibility with frozen schemas

The following current values have been directly validated against the frozen
Release Build Record schema:

| Field | Value | Result |
| --- | --- | --- |
| `os_release_identity` | `ubuntu-24.04` | PASS |
| `libc_identity` | `glibc-2.39` | PASS |
| `locale_identity` | `C.UTF-8` | PASS |
| `timezone_identity` | `America/New_York` | PASS |
| `os_runtime_identity` | `system-Linux+release-ubuntu-24.04+kernel-6.17.0-35-generic+libc-glibc-2.39` | PASS |

The clarification does not add a field or change an existing field grammar.
The locale algorithm produces one scalar value, timezone acquisition produces
a bounded nonempty string, and every OS/libc component retains the frozen
component grammar.

## 41. Tooling declaration compatibility

The current project metadata already has a `[project.optional-dependencies]`
table containing the `test` extra. A distinct `release-integrity` extra with
the exact `packaging==24.0` pin can be added later without changing
`project.dependencies` or the existing test extra. No such edit is performed
by this clarification.

## 42. Registry projection compatibility

All nine frozen registry records are representable without changing a field in
the proposed frozen dataclass and immutable tuple. No existing public project
API uses `GoverningDocumentRegistryEntry` or
`GOVERNING_DOCUMENT_REGISTRY_V0_1` with an incompatible meaning.

The public projection is a transparent implementation of the one normative
Markdown registry, not an independently editable registry.

## 43. Implementation gate

This document is design only. It does not implement Stage 12E-2, declare the
tooling extra, create registry code, assemble release artifacts, create or move
tags, install packages, or authorize runtime research.

Stage 12E-2 may begin only after this clarification is separately reviewed,
approved, and frozen.
