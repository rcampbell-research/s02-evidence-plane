# Process-Stability and Regression-Verification Method Clarification v0.1

## 1. Status and purpose

This document freezes the engineering regression-verification method named
`segmented-complete-suite-v0.1`. It exists because repeated fatal Python
process terminations make a single long-lived pytest interpreter an unreliable
source of exact-byte complete-suite provenance.

The normative answer is **YES**: one monolithic pytest process is not required
for implementation-freeze provenance. Subject to every safeguard in this
document, deterministic complete-suite execution with one test module per
fresh Python process is sufficient exact-byte regression evidence for an
implementation freeze.

The method does not reduce the regression standard. Every nodeid in the global
collection MUST execute exactly once, no module may be omitted, and no failed
or fatal segment may be retried under the same authorization. Segmentation
changes process lifetime only; it does not change the required tests.

This is a methodology clarification only. It does not execute tests, modify an
implementation, change a schema, create a runtime result, or establish a
scientific result.

## 2. Frozen base and current candidate

The clarification base is:

```text
73bc95ee98c4de4391c4d772188d5add71a38b3b
```

Required predecessor tags and peeled targets are:

| Milestone | Peeled target |
| --- | --- |
| `iv-g6-inert-runtime-adapter-clarification-v0.1` | `73bc95ee98c4de4391c4d772188d5add71a38b3b` |
| `implementation-iv-g5-orchestration-state-machines-v0.1` | `b053347e3f9440c49e684fe423677efe98f1e60c` |

The current untracked IV-G6 candidate remains exactly:

| Path | Lines | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `src/frontier_agent_containment/instrument_validation/adapters.py` | 1538 | 69256 | `2e389f742e5031868ac3cd9489c1619506f3cf66fcdd94cfa7a4f043b763b36f` |
| `src/frontier_agent_containment/instrument_validation/s0.py` | 105 | 4431 | `8bd4dd59942fc1d338c47dc9bea8e682af97b67e06aaa6f2e8c869f634a338df` |
| `src/frontier_agent_containment/instrument_validation/observers.py` | 99 | 3453 | `d1562d34d8513d0cbb74e194a47811492f3a6b84491c961749d25fa5ebddd856` |
| `tests/instrument_validation/test_runtime_adapters_static.py` | 1412 | 67540 | `7010d0cbec6f5bbeca685bc163e0e145a52c3b6449ed1a697e60eee8edf8a697` |

This clarification MUST NOT alter those files or identities.

## 3. Preserved test evidence

The predecessor complete-suite baseline is 3797 passing tests. The exact final
IV-G6 test bytes have produced 336 focused passing tests. Global collection on
the exact final candidate produced 4133 nodeids, satisfying:

```text
3797 + 336 = 4133
```

A historical monolithic run produced 4133 passing tests before removal of one
semantically inert EOF blank line from the G6 test file. That run is historical
context, not exact-final-byte complete-suite provenance. The focused 336 result
remains valid but does not substitute for the complete segmented verification.

## 4. Fatal-process history

Two fatal-process events are recorded without causal attribution.

### 4.1 Event A: prior Stage12E4 termination

The prior Stage12E4 process terminated with SIGSEGV. It was classified as a
transient, non-reproduced process termination. Subsequent bounded recovery at
that milestone completed successfully. Its root cause remains unknown.

### 4.2 Event B: final-byte G6 monolithic verification

The exact-final-byte monolithic G6 verification attempt terminated with
SIGSEGV, exit status 139, at approximately 62 percent progress. The observed
stack was in jsonschema schema validation during
`tests/reproducibility/test_stage12e5_fixed_release_corpus.py`. No ordinary
pytest failure had appeared, no candidate byte changed, no core file was
found, and no automatic retry was performed.

The root cause remains unknown. This document does not attribute either event
to G6, Stage12E5, jsonschema, Python, the kernel, memory, hardware, or any other
component.

## 5. Functional failure and process-stability failure

The method distinguishes two blocker classes.

**Functional regression failure** means an assertion failure, test error,
collection mismatch, deterministic contract failure, missing test, extra test,
or manifest/set mismatch reported through ordinary test or verification
behavior.

**Process-stability failure** means SIGSEGV, SIGABRT, a fatal interpreter or
native-extension termination, signal-derived exit, or another abnormal process
exit that is not an ordinary pytest assertion/result.

Both classes block the authoritative run. A process-stability failure MUST NOT
be reported as a test assertion failure, and an assertion failure MUST NOT be
obscured as process instability.

## 6. Monolithic retry policy

No further monolithic complete-suite retry is required or authorized merely to
seek a favorable result after the repeated process-level SIGSEGV events. A
successful result obtained by repeating the same crashing monolithic command
until it passes would weaken provenance and is prohibited.

Future reports MUST use this wording unless later evidence changes it:

```text
Monolithic complete-suite verification: unavailable/unreliable due repeated
non-deterministic process-level SIGSEGV events; no semantic pytest failure was
established by those terminations.
```

## 7. Approved authoritative method

The approved method identifier is:

```text
segmented-complete-suite-v0.1
```

The report label is:

```text
Segmented Complete Suite: <passed> / <globally-collected> passed
```

One segment is one pytest-collected repository test module, identified by its
exact repo-relative path. Segment order is lexicographically ascending by
repo-relative module path under `LC_ALL=C`. Segment boundaries are fixed from
the global collection before any test segment executes and cannot be changed
after outcomes are observed.

Each module is executed sequentially in its own fresh Python interpreter. No
xdist, parallel worker pool, test randomization, nodeid selector, marker
selector, keyword selector, or outcome-dependent sharding is permitted.

## 8. Module-level segmentation viability

A read-only audit at this clarification base established:

- `pyproject.toml` contains the sole pytest configuration and declares only
  `pythonpath = ["src"]` and `testpaths = ["tests"]`;
- no repository `conftest.py` exists;
- no session-scoped pytest fixture exists;
- all declared fixtures are function- or module-scoped;
- module-scoped fixtures are reconstructed within their owning module process;
- pytest `monkeypatch` use is function-scoped/context-scoped and restored by
  pytest;
- filesystem-writing tests operate on pytest temporary paths or copies made
  for the owning test/module;
- no pytest ordering, dependency, randomization, or xdist plugin is configured;
- no test declares that correctness depends on a previously executed module;
  and
- no mutable global cache, schema store, environment mutation, or import-order
  effect is intentionally required across test modules for correctness.

Module-local constants and module-local fixture data are not cross-module
semantic state. Import caches inside one segment are permitted only as normal
in-process implementation details; no later segment may depend on them.

Therefore the current repository has no intended semantic cross-module state
dependency, no session-fixture persistence requirement, and no test-order
dependency that prevents module-per-process verification. If a future audit
finds such a dependency, this method becomes invalid for that candidate and
verification MUST STOP before segment execution.

## 9. Mandatory pre-verification state audit

Before a future authoritative run, a read-only audit MUST repeat checks for:

- new `conftest.py` files or pytest plugins;
- session/package fixtures spanning modules;
- cross-module monkeypatching or module replacement;
- environment/current-directory mutations not restored by fixtures;
- import-order or prior-module assumptions;
- persistent filesystem paths shared for semantic state;
- mutable global schema stores or caches required for correctness; and
- ordering, dependency, randomization, xdist, or parallel-execution plugins.

Any semantic cross-module dependency is a blocker. A session fixture used only
as reconstructible setup optimization MAY be converted naturally into
per-module setup by the fresh process; a fixture whose value must persist from
one test module to another makes module segmentation invalid.

## 10. Temporary provenance storage

Temporary manifests and logs MUST be stored outside the repository in one
newly created directory under `/tmp`. The exact initialization is:

```bash
METHOD_TMPDIR="$(mktemp -d /tmp/segmented-complete-suite-v0.1.XXXXXXXXXX)"
export METHOD_TMPDIR
```

All protocol commands MUST run from the repository root. The driver records
that absolute starting directory with `pwd` and MUST NOT change directory
during collection or segment execution.

No manifest, log, helper script, or result table may be written into the
repository. The temporary directory MUST remain available until the final
report records all required values. It MAY be removed after the report is
complete. Its cleanup neither changes nor repairs candidate provenance.

Shell-memory processing is permitted, but the authoritative current procedure
uses temporary files so manifests and per-segment logs remain inspectable.

## 11. Candidate hash manifest and gates

For the current IV-G6 candidate, create this exact temporary checksum file:

```bash
printf '%s  %s\n' \
  '2e389f742e5031868ac3cd9489c1619506f3cf66fcdd94cfa7a4f043b763b36f' \
  'src/frontier_agent_containment/instrument_validation/adapters.py' \
  '8bd4dd59942fc1d338c47dc9bea8e682af97b67e06aaa6f2e8c869f634a338df' \
  'src/frontier_agent_containment/instrument_validation/s0.py' \
  'd1562d34d8513d0cbb74e194a47811492f3a6b84491c961749d25fa5ebddd856' \
  'src/frontier_agent_containment/instrument_validation/observers.py' \
  '7010d0cbec6f5bbeca685bc163e0e145a52c3b6449ed1a697e60eee8edf8a697' \
  'tests/instrument_validation/test_runtime_adapters_static.py' \
  > "$METHOD_TMPDIR/candidate.sha256"
```

Every gate uses:

```bash
sha256sum -c "$METHOD_TMPDIR/candidate.sha256"
```

The gate MUST pass:

1. before global collection;
2. after global collection and manifest construction;
3. immediately before segmented execution;
4. immediately before each module's collection/execution pair;
5. immediately after every module execution, including a failed/fatal one;
6. after nodeid-union verification; and
7. at final repository audit.

Per-module checking is mandatory for v0.1; no coarser batch is allowed. Any
hash mismatch stops the run and makes the entire run non-authoritative. Any
candidate edit after global manifest creation makes all results from that
manifest historical and requires a separately authorized complete repetition
on the new bytes.

## 12. Environment provenance

Before collection, record without altering the repository:

```bash
pwd > "$METHOD_TMPDIR/repository-root.txt"
git rev-parse HEAD > "$METHOD_TMPDIR/head.txt"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python --version \
  > "$METHOD_TMPDIR/python-version.txt" 2>&1
printf '%s\n' \
  'PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider --collect-only -q' \
  > "$METHOD_TMPDIR/global-collection-command.txt"
printf '%s\n' \
  'PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 .venv/bin/python -X faulthandler -m pytest -p no:cacheprovider -q <repo-relative-module>' \
  > "$METHOD_TMPDIR/segment-command-template.txt"
```

The report MUST record HEAD, Python version, both invocation strings, and the
candidate hash manifest digest. Documentation-only advancement of HEAD after
this clarification is frozen does not invalidate G6 candidate semantics if all
four candidate hashes remain exact. The later report MUST record that new HEAD
and the methodology-clarification commit as the G6 implementation parent.

## 13. Global collection manifest

Run global collection exactly once on the candidate bytes:

```bash
set +e
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
    -p no:cacheprovider --collect-only -q \
    > "$METHOD_TMPDIR/global-collection.stdout" \
    2> "$METHOD_TMPDIR/global-collection.stderr"
COLLECTION_EXIT=$?
set -e
test "$COLLECTION_EXIT" -eq 0
```

Extract and canonically sort exact nodeids:

```bash
LC_ALL=C sed -n '/^tests\/.*\.py::/p' \
  "$METHOD_TMPDIR/global-collection.stdout" \
  | LC_ALL=C sort \
  > "$METHOD_TMPDIR/global-nodeids.txt"

awk '$2 ~ /^tests?$/ && $3 == "collected" && $4 == "in" {print $1}' \
  "$METHOD_TMPDIR/global-collection.stdout" \
  > "$METHOD_TMPDIR/global-reported-count.txt"

awk 'END {print NR}' "$METHOD_TMPDIR/global-nodeids.txt" \
  > "$METHOD_TMPDIR/global-manifest-count.txt"

cmp -s \
  "$METHOD_TMPDIR/global-reported-count.txt" \
  "$METHOD_TMPDIR/global-manifest-count.txt"
```

For the current candidate both counts MUST equal 4133. The parser accepts only
repo test nodeids beginning with `tests/` and containing a `.py::` module/node
separator. Any reported/parsed count mismatch stops verification.

Prove that no global nodeid is duplicated:

```bash
LC_ALL=C uniq -d "$METHOD_TMPDIR/global-nodeids.txt" \
  > "$METHOD_TMPDIR/duplicate-global-nodeids.txt"
test ! -s "$METHOD_TMPDIR/duplicate-global-nodeids.txt"
```

The canonical `global-nodeids.txt` is the authoritative ordered nodeid
manifest. Its SHA-256 MUST be recorded.

## 14. Immutable module manifest

Derive modules mechanically from the global nodeids; manual selection is
prohibited:

```bash
sed 's/::.*$//' "$METHOD_TMPDIR/global-nodeids.txt" \
  | LC_ALL=C sort -u \
  > "$METHOD_TMPDIR/modules.txt"

test -s "$METHOD_TMPDIR/modules.txt"
LC_ALL=C sort "$METHOD_TMPDIR/modules.txt" \
  | LC_ALL=C uniq -d \
  > "$METHOD_TMPDIR/duplicate-modules.txt"
test ! -s "$METHOD_TMPDIR/duplicate-modules.txt"
```

Validate every manifest entry before execution:

```bash
while IFS= read -r MODULE_PATH; do
  case "$MODULE_PATH" in
    tests/*.py) ;;
    *) exit 1 ;;
  esac
  test -f "$MODULE_PATH"
done < "$METHOD_TMPDIR/modules.txt"
```

Record:

```bash
wc -l "$METHOD_TMPDIR/modules.txt"
sha256sum "$METHOD_TMPDIR/global-nodeids.txt"
sha256sum "$METHOD_TMPDIR/modules.txt"
sha256sum "$METHOD_TMPDIR/candidate.sha256"
```

The ordered `modules.txt` is immutable for the run. Its digest is the segment-
manifest digest. No module can be added, removed, duplicated, reordered, or
split after execution starts.

## 15. Per-module collection proof

Each module MUST be separately collected once immediately before its one test
execution attempt. This collection is not a test execution attempt. It proves
that the module's current collection equals the corresponding subset of the
global manifest.

For module ordinal `NNNN` and exact `$MODULE_PATH`:

```bash
awk -v prefix="$MODULE_PATH::" \
  'index($0, prefix) == 1' \
  "$METHOD_TMPDIR/global-nodeids.txt" \
  > "$METHOD_TMPDIR/segment-NNNN.expected-nodeids.txt"
test -s "$METHOD_TMPDIR/segment-NNNN.expected-nodeids.txt"

set +e
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
    -p no:cacheprovider --collect-only -q "$MODULE_PATH" \
    > "$METHOD_TMPDIR/segment-NNNN.collection.stdout" \
    2> "$METHOD_TMPDIR/segment-NNNN.collection.stderr"
SEGMENT_COLLECTION_EXIT=$?
set -e
test "$SEGMENT_COLLECTION_EXIT" -eq 0

LC_ALL=C sed -n '/^tests\/.*\.py::/p' \
  "$METHOD_TMPDIR/segment-NNNN.collection.stdout" \
  | LC_ALL=C sort \
  > "$METHOD_TMPDIR/segment-NNNN.collected-nodeids.txt"

awk '$2 ~ /^tests?$/ && $3 == "collected" && $4 == "in" {print $1}' \
  "$METHOD_TMPDIR/segment-NNNN.collection.stdout" \
  > "$METHOD_TMPDIR/segment-NNNN.reported-count.txt"

awk 'END {print NR}' \
  "$METHOD_TMPDIR/segment-NNNN.collected-nodeids.txt" \
  > "$METHOD_TMPDIR/segment-NNNN.manifest-count.txt"

cmp -s \
  "$METHOD_TMPDIR/segment-NNNN.reported-count.txt" \
  "$METHOD_TMPDIR/segment-NNNN.manifest-count.txt"

cmp -s \
  "$METHOD_TMPDIR/segment-NNNN.expected-nodeids.txt" \
  "$METHOD_TMPDIR/segment-NNNN.collected-nodeids.txt"
```

The collection process MUST exit zero, its parsed/reported counts MUST agree,
the expected set MUST be nonempty, and `cmp` MUST succeed. A mismatch, fatal
collection process, unexpected module, or empty expected set stops the run
before that module executes.

## 16. One fresh-process execution per segment

Each module then receives exactly one authoritative execution attempt:

```bash
set +e
PYTHONDONTWRITEBYTECODE=1 \
PYTHONFAULTHANDLER=1 \
  .venv/bin/python -X faulthandler -m pytest \
    -p no:cacheprovider -q "$MODULE_PATH" \
    > "$METHOD_TMPDIR/segment-NNNN.execution.log" 2>&1
SEGMENT_EXIT=$?
set -e
```

The module path is the sole pytest selector. No nodeid, marker, keyword,
failure history, or historical result may alter the invocation.

Extract and validate the exact passing summary:

```bash
awk '$2 == "passed" && $3 == "in" {print $1}' \
  "$METHOD_TMPDIR/segment-NNNN.execution.log" \
  > "$METHOD_TMPDIR/segment-NNNN.passed-count.txt"

test "$(awk 'END {print NR}' \
  "$METHOD_TMPDIR/segment-NNNN.passed-count.txt")" -eq 1

cmp -s \
  "$METHOD_TMPDIR/segment-NNNN.manifest-count.txt" \
  "$METHOD_TMPDIR/segment-NNNN.passed-count.txt"

SEGMENT_FATAL=none
if test "$SEGMENT_EXIT" -ge 128; then
  SEGMENT_FATAL="signal:$((SEGMENT_EXIT - 128))"
fi
if rg -q 'Fatal Python error|Segmentation fault|Aborted' \
  "$METHOD_TMPDIR/segment-NNNN.execution.log"; then
  SEGMENT_FATAL=detected
fi
```

The segment passes only when `SEGMENT_EXIT` is zero, `SEGMENT_FATAL` is
`none`, the count comparison succeeds, and the post-segment hash gate passes.
The driver MUST capture and record diagnostic output before stopping on any
other result.

Elapsed seconds may be measured by the driver shell solely as engineering log
provenance; elapsed time is not a test input, runtime-provider fact, or
scientific datum.

## 17. Passed-segment attestation

A segment contributes evidence only when all of these hold:

- the pre-segment candidate hash gate passed;
- per-module collection exactly matched the global-manifest subset;
- execution exit status is zero;
- the execution summary reports exactly the expected number passed;
- no skipped, deselected, xfailed, xpassed, errored, or failed test replaces a
  required pass;
- no fatal signal or fatal-interpreter output occurred; and
- the post-segment candidate hash gate passed.

After those checks, and only then, append that segment's exact collected
nodeids to `executed-nodeids.unsorted.txt`. This is an attestation that the
module-path-only invocation executed and passed every nodeid in its separately
verified collection.

Append one row to `segment-results.tsv` with:

```text
ordinal  module  collected  passed  exit  elapsed_seconds  fatal  post_hash
```

The future report MUST include every row, not only failures. `fatal` is `none`
for a normal process or the observed signal/abnormal termination. `post_hash`
is `MATCH` only after all four candidate checks pass.

## 18. One-attempt, failure, and fatal rules

Every module gets exactly one execution attempt in an authoritative run.

If a segment produces an ordinary failure, test error, collection mismatch,
fatal signal, abnormal nonzero exit, unexpected summary, or hash mismatch, the
driver MUST:

1. record the module row and available diagnostics;
2. perform the read-only post-segment candidate hash check;
3. stop immediately;
4. not rerun the segment;
5. not continue to later modules; and
6. not substitute any historical focused, module, or full-suite result.

A SIGSEGV exit 139 at module scope is a process-stability blocker localized to
that bounded module process. It requires a separate targeted investigation and
does not authorize a retry.

A later attempt after any failed authoritative run requires separate explicit
authorization and a documented reason. Silent retry-until-pass is prohibited.

## 19. Complete nodeid-union proof

After all modules pass, canonicalize the attested executed union:

```bash
LC_ALL=C sort "$METHOD_TMPDIR/executed-nodeids.unsorted.txt" \
  > "$METHOD_TMPDIR/executed-nodeids.txt"

LC_ALL=C uniq -d "$METHOD_TMPDIR/executed-nodeids.txt" \
  > "$METHOD_TMPDIR/duplicate-executed-nodeids.txt"
test ! -s "$METHOD_TMPDIR/duplicate-executed-nodeids.txt"

cmp -s \
  "$METHOD_TMPDIR/global-nodeids.txt" \
  "$METHOD_TMPDIR/executed-nodeids.txt"

sha256sum "$METHOD_TMPDIR/global-nodeids.txt"
sha256sum "$METHOD_TMPDIR/executed-nodeids.txt"
```

The two digests MUST be identical. Exact set equality, not merely count
equality, proves no missing, duplicate, substituted, or extra nodeid.

## 20. Global arithmetic and result-table verification

The future driver MUST verify:

```text
number of successful segment rows = number of module-manifest rows
sum(segment collected) = global collection count
sum(segment passed) = global collection count
executed-nodeid count = global collection count
global nodeid digest = executed nodeid digest
```

For the current exact candidate the required result is:

```text
global collection                 4133
sum segment collected             4133
sum segment passed                4133
executed nodeid manifest          4133 unique nodeids
Segmented Complete Suite          4133 / 4133 passed
ordinary failures                 0
fatal segment signals             0
```

An exact shell summation template is:

```bash
awk -F '\t' 'NR > 1 {collected += $3; passed += $4}
  END {print collected, passed}' \
  "$METHOD_TMPDIR/segment-results.tsv" \
  > "$METHOD_TMPDIR/segment-sums.txt"

wc -l < "$METHOD_TMPDIR/global-nodeids.txt"
wc -l < "$METHOD_TMPDIR/executed-nodeids.txt"
wc -l < "$METHOD_TMPDIR/modules.txt"
```

Count equality supplements but never replaces the `cmp` and digest equality
proof.

## 21. No cherry-picking or historical stitching

The method prohibits:

- running only historically problematic modules;
- omitting slow modules, including Stage12E5, Stage12E4, or Stage12E3;
- changing segment boundaries or ordering after observing results;
- rerunning a failed/fatal segment;
- using a historical pass for a current failed or unexecuted segment;
- stitching earlier G5, G4, G6, Stage12E, identity, or full-suite runs into the
  authoritative segmented total; and
- reporting partial completion as a segmented complete-suite pass.

Historical module results may be listed as context only. Every globally
collected module and nodeid executes once in the current authoritative run.

## 22. Equivalence and claim boundary

A successful segmented verification proves exactly:

> Every required globally collected regression test passed once on the exact
> candidate bytes under the recorded Python/environment configuration, with
> each test module isolated in a fresh interpreter process, no omitted or
> duplicate nodeid, no ordinary failure, and no fatal segment signal.

It does not prove process-level equivalence to one monolithic interpreter and
does not prove the absence of long-lived cross-module interpreter-state
interactions. Such interactions are not an intended product or test property;
the mandatory static audit must continue to establish that no semantic
cross-module dependency is required.

If all safeguards pass, `segmented-complete-suite-v0.1` is normatively
sufficient exact-byte regression evidence for implementation freeze. A
monolithic pass is not additionally required.

If all module segments pass, reports MUST state only that the fatal termination
did not reproduce at bounded module-process scope under this protocol. They
MUST NOT claim either SIGSEGV root cause was found or fixed. Root cause remains
unknown.

## 23. Required freeze provenance

A later verification/freeze report MUST record:

- method identifier `segmented-complete-suite-v0.1`;
- final exact candidate hashes;
- current HEAD and methodology-clarification commit;
- focused G6 result, separately labeled;
- Python version and exact collection/execution commands;
- global collection count;
- canonical global-nodeid manifest SHA-256;
- module count and canonical module-manifest SHA-256;
- every segment row: ordinal, module, collected, passed, exit, elapsed, fatal,
  and post-segment hash status;
- summed collected and passed counts;
- canonical executed-nodeid SHA-256;
- equality of global/executed nodeid manifests and digests;
- zero ordinary failures and zero fatal segment signals;
- final candidate hash gate;
- repository/transient audit; and
- confirmation that no monolithic retry or historical substitution was used.

## 24. Failure handling summary

| Condition | Required result |
| --- | --- |
| Global collection nonzero/fatal | STOP; no segment execution |
| Global reported/parsed count mismatch | STOP |
| Duplicate global nodeid | STOP |
| Missing, extra, duplicate, or invalid module | STOP |
| Per-module collection mismatch | STOP before module execution |
| Ordinary segment failure/error | Record and STOP; no retry |
| Fatal/abnormal segment process | Record and STOP; no retry |
| Candidate hash mismatch | STOP; entire run non-authoritative |
| Executed/global nodeid mismatch | STOP |
| Historical pass exists for failed segment | No substitution; current run fails |
| Candidate edit after manifest creation | Entire run historical; new authorization required |

## 25. Static prototype A: complete coverage

Suppose the global canonical manifest has ten nodeids:

```text
tests/a/test_a.py::test_1
tests/a/test_a.py::test_2
tests/a/test_a.py::test_3
tests/b/test_b.py::test_1
tests/b/test_b.py::test_2
tests/b/test_b.py::test_3
tests/b/test_b.py::test_4
tests/c/test_c.py::test_1
tests/c/test_c.py::test_2
tests/c/test_c.py::test_3
```

The derived module manifest has three lexical segments with 3, 4, and 3
nodeids. Each module collection equals its global subset, each executes once,
and the canonical union contains the same ten lines with the same digest.
There is no gap or overlap. **Prototype A: PASS.**

## 26. Static prototype B: ordinary module failure

Segment 1 passes. Segment 2 reports an ordinary assertion failure. Segment 2
is recorded once; it is not rerun, segment 3 is not started, and the segmented
suite is STOPPED. **Prototype B: PASS.**

## 27. Static prototype C: module SIGSEGV

A fresh module process exits 139 with SIGSEGV. The driver records the fatal
termination and post-segment hashes, stops immediately, performs no retry, and
does not substitute a historical module pass. **Prototype C: PASS.**

## 28. Static prototype D: candidate hash change

After segment N, one candidate digest differs. The driver stops before segment
N+1 and marks the entire run non-authoritative even if all completed tests had
passed. Restoring bytes does not revive that run. **Prototype D: PASS.**

## 29. Static prototype E: missing module

The global manifest contains `tests/x/test_x.py::test_one`, but the proposed
module manifest omits `tests/x/test_x.py`. Because the module manifest must be
derived mechanically from global nodeids, validation fails before
authoritative completion. **Prototype E: PASS.**

## 30. Static prototype F: duplicate module

If a module appears twice in a proposed segment manifest, the uniqueness check
fails. No segment execution begins. **Prototype F: PASS.**

## 31. Static prototype G: equal counts, different nodeids

An executed union contains ten nodeids, but one expected nodeid is replaced by
an extra different nodeid. Counts remain ten, but canonical `cmp` and SHA-256
equality fail. The run is not authoritative. **Prototype G: PASS.**

## 32. Static prototype H: historical pass

A current segment fails while a prior run of that module passed. The current
segmented verification fails; historical evidence is reported only as context
and cannot fill the segment. **Prototype H: PASS.**

## 33. Static prototype I: all segments pass

Every immutable-manifest module is collected exactly, receives one execution
attempt, exits zero, passes every expected nodeid, emits no fatal signal, and
leaves all candidate hashes unchanged. The executed/global canonical manifests
and digests match. The result is `Segmented Complete Suite: PASS`.
**Prototype I: PASS.**

## 34. Static prototype J: cross-module state

In a hypothetical repository where module A must mutate process state before
module B can pass, module segmentation is invalid because it cannot verify the
intended semantics. The current repository's no-session-fixture,
no-conftest, no-order-plugin, reconstructible-fixture audit establishes that no
such intended dependency exists. A future contrary finding forces STOP.
**Prototype J: PASS.**

## 35. Semantic-totality checklist

| Requirement | Closed |
| --- | --- |
| Functional/process failure distinction | YES |
| No further monolithic retry rule | YES |
| Deterministic module segment definition | YES |
| Fresh process per module | YES |
| Complete canonical nodeid manifest | YES |
| Immutable module manifest | YES |
| One global collection | YES |
| Exact global/executed nodeid set equality | YES |
| No duplicate nodeids | YES |
| No omitted nodeids | YES |
| Exact-byte hash gates | YES |
| One execution attempt per segment | YES |
| Ordinary failure stops | YES |
| Fatal signal stops | YES |
| Historical results cannot substitute | YES |
| No cherry-picking | YES |
| No retry-until-pass | YES |
| Cross-module-state audit | YES |
| Session-fixture audit | YES |
| Test-order-independence requirement | YES |
| Every collected module mandatory | YES |
| Expensive modules retained | YES |
| Candidate edits invalidate the run | YES |
| Precise segmented-result terminology | YES |
| Bounded equivalence claim | YES |
| Monolithic status reporting | YES |
| Segmented method sufficient for freeze | YES |
| Complete provenance fields | YES |
| GREEN boundary | YES |
| Scientific non-impact | YES |

Result: **30/30 YES**. No implementation-significant methodology item remains
open.

## 36. GREEN and RED boundary

Segmented regression verification is GREEN engineering verification. It does
not authorize provider invocation, actor/scenario execution, network activity,
real reset, timers, fault injection, resource or S0 observation, evidence
collection, S0 acceptance, M3 enforcement, runtime Instrument Validation,
Pilot, or Confirmatory execution.

The method changes no H1, Y, primary unit, M3-versus-M1 estimand, G4 semantics,
G5 semantics, G6 semantics, null-result rule, Pilot rule, or Confirmatory rule.
It produces no runtime evidence or scientific result.

## 37. Inventory non-impact

This methodology introduces no schema, registry, component, authority source,
authority property, scientific artifact family, or family/version pair.
Preserved inventories are:

| Inventory | Count |
| --- | ---: |
| Generic schemas | 36 |
| IV-core schemas | 24 |
| Scientific families | 21 |
| Family/version pairs | 26 |
| Corrected authority | 17 properties / 15 sources |
| Historical authority | 16 properties / 15 sources |

## 38. Documentation-only HEAD advancement

Freezing this documentation before segmented verification will advance HEAD
while the four G6 files remain untracked. That documentation-only advancement
does not invalidate G6 candidate semantics or prior focused evidence provided
all four candidate hashes remain exact. The authoritative segmented run must
record the new HEAD and must apply all hash gates to those untracked bytes.

## 39. Required milestone order

The authorized order after this clarification is:

1. freeze this Process-Stability and Regression-Verification Method
   Clarification v0.1;
2. execute one separately authorized `segmented-complete-suite-v0.1` run on
   the exact final G6 candidate bytes;
3. perform the final read-only G6 pre-commit review;
4. stage and freeze the G6 implementation; and
5. continue to IV-G7 only after separate authorization.

No further monolithic suite retry is required.

## 40. Future clarification tag

The exact future annotated clarification tag is:

```text
process-stability-regression-verification-method-clarification-v0.1
```

This document does not create the tag.

## 41. Findings and next authorization

At clarification completion:

- BLOCKER: none;
- MAJOR: none;
- MINOR: none; and
- DEFERRED: freezing this clarification, authoritative segmented exact-byte G6
  verification, final G6 freeze review, G6 implementation freeze, IV-G7,
  IV-R1 through IV-R5, and all runtime/scientific work.

The Process-Stability and Regression-Verification Method Clarification v0.1 is
semantically ready to freeze. The approved method is
`segmented-complete-suite-v0.1`. No verification is executed by this document,
and no further monolithic pytest retry is required for IV-G6 freeze provenance.
