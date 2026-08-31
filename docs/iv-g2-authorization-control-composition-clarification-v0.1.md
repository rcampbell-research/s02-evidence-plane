# IV-G2 Authorization-versus-Control Composition Clarification v0.1

## 1. Status and purpose

This is a narrow design clarification for IV-G2 Actor and Control Decisions
v0.1. It resolves one conflict introduced by the later implementation
authorization. It does not amend unrelated script, authorization, approval,
M1, M2, M3, identity, diagnostic, or schema semantics.

The frozen predecessor is:

~~~text
iv-g2-actor-control-decisions-clarification-v0.1
20edaf30bc375ffa5b7138bafd8f42ae5bba7955
~~~

Its frozen document SHA-256 is:

~~~text
fa68d1906e92c2bd21306c23afe637c61554ee29add8cb818d1f21b7b4a01b2d
~~~

The required IV-G1 implementation predecessor remains:

~~~text
implementation-iv-g1-runtime-contracts-v0.1
ec3fb9126c3c9cc7e54a85fd232711d024d498f4
~~~

The preserved implementation baseline remains 2231 passed with zero failures.
The historical SIGSEGV remains non-reproduced with unknown root cause. This
document does not reinterpret it.

## 2. Exact contradiction

The frozen IV-G2 clarification defines:

~~~text
authorization decision DENIED
    -> authorization posture UNAUTHORIZED
~~~

It also defines the following exact M1 row:

~~~text
configuration ACTIVE
delivery DELIVERED
authorization posture UNAUTHORIZED
actor response IGNORE_CONTEXT
    -> selected M1 control decision PROCEED
~~~

The later implementation authorization required a blanket test asserting:

~~~text
DENIED authorization cannot produce control PROCEED
~~~

That assertion incorrectly equates an authorization result with a selected
treatment response. It contradicts the frozen M1 row. The blanket assertion is
withdrawn and must not be implemented.

This is an implementation-requirement contradiction, not a contradiction in
the frozen scientific design.

## 3. Governing scientific distinction

The governing Control Architecture Specification makes M1 behavioral and
subject-dependent:

- the capability envelope and external policy remain the authoritative
  normative statement of permission;
- the model or scripted subject may follow or ignore supplied policy context;
- M1 behavior cannot grant authority;
- M1 has no independent prevention mechanism; and
- runtime containment cannot be inferred from model or subject behavior alone.

The Research Contract studies whether controls prevent unauthorized
consequential effects. It does not assume M1 always complies. Preserving a
permissive M1 response to an independently unauthorized request is therefore
necessary to represent the intended M1 treatment contrast.

No earlier frozen scientific or control contract requires M1 to return BLOCK
for the IGNORE_CONTEXT row. The frozen row is preserved unchanged.

## 4. Three separate semantic dimensions

IV-G2 preserves three separate dimensions.

### 4.1 Authorization decision

The closed authorization-decision vocabulary remains:

~~~text
ALLOWED
DENIED
APPROVAL_REQUIRED
INDETERMINATE
~~~

This is the normative evaluation made against the independently supplied
capability envelope and authorization policy.

### 4.2 Authorization posture

Authorization posture is the internal classification derived only from the
authorization decision and, when required, its bound approval decision:

~~~text
AUTHORIZED
UNAUTHORIZED
INDETERMINATE
~~~

It remains an internal derived value. It is not an execution token, a final
permission, or a separately persisted artifact.

### 4.3 Selected control decision

The closed selected-control vocabulary remains:

~~~text
PROCEED
BLOCK
INDETERMINATE
~~~

This answers only how the selected M1, M2, or M3 treatment calculation responds
to the supplied valid inputs.

These dimensions are not aliases. A selected control decision does not rewrite
the authorization decision or posture. Authorization is not inferred from a
selected control decision.

## 5. Authorization invariance

The authorization decision is immutable after it is produced.

If the decision is DENIED:

- the decision remains DENIED under every approval candidate;
- the authorization posture remains UNAUTHORIZED;
- no selected control result can change either value; and
- neither PROCEED nor any other control result creates authorization.

If the decision is INDETERMINATE:

- the decision remains INDETERMINATE;
- the authorization posture remains INDETERMINATE; and
- no selected control result converts it to ALLOWED or AUTHORIZED.

If the decision is APPROVAL_REQUIRED:

- the authorization decision remains APPROVAL_REQUIRED;
- only the frozen approval composition determines posture;
- a selected control result cannot remove the approval requirement; and
- the original decision is not rewritten to ALLOWED after approval.

If the decision is ALLOWED, it remains ALLOWED. A control BLOCK or
INDETERMINATE does not rewrite it to DENIED; the distinct control result is
preserved beside it.

The exact invariant is:

~~~text
control decisions cannot confer, revoke, or rewrite authorization
~~~

## 6. Approval non-override

Approval is evaluated only for a valid APPROVAL_REQUIRED authorization
decision. A candidate approval attached to ALLOWED, DENIED, or INDETERMINATE is
a binding contradiction and is rejected before selected-control evaluation.

In particular, APPROVED cannot override DENIED. A hostile, malformed, replayed,
or otherwise extraneous approval candidate does not change the already
recorded DENIED decision.

When approval is required:

- APPROVED derives posture AUTHORIZED;
- REJECTED derives posture UNAUTHORIZED;
- EXPIRED derives posture UNAUTHORIZED;
- TIMED_OUT derives posture UNAUTHORIZED;
- UNAVAILABLE derives posture INDETERMINATE;
- INVALID derives posture INDETERMINATE; and
- an absent approval record yields an incomplete posture INDETERMINATE.

The selected control consumes the derived posture but cannot repair or replace
the approval result.

## 7. Exact PROCEED semantics

PROCEED means only:

~~~text
the selected pure IV-G2 treatment calculation returns a permissive
control-layer response for the supplied validated inputs
~~~

It does not mean:

~~~text
AUTHORIZED
EXECUTION_ELIGIBLE
EXECUTION_DISPATCHED
EXECUTED
EFFECT_OBSERVED
SUCCESSFUL
SAFE
~~~

This definition applies uniformly to M1, M2, and M3.

The scientifically important combination:

~~~text
authorization decision DENIED
authorization posture UNAUTHORIZED
selected M1 control decision PROCEED
~~~

means that M1 would proceed despite the independently unauthorized posture. It
does not mean authorization changed or that an action executed.

## 8. Exact BLOCK and control-INDETERMINATE semantics

BLOCK means only that the selected pure treatment calculation returns a
blocking response. It does not prove:

- a runtime gate existed;
- enforcement occurred;
- dispatch was prevented;
- the action did not execute; or
- no consequential effect occurred.

Control INDETERMINATE means only that the selected pure treatment calculation
could not produce an ordinary permissive or blocking response under its frozen
valid fault-state inputs. It does not change an authorization decision and
never becomes authorization.

Runtime claims require later authoritative execution, enforcement, resource,
effect, collection, and derivation evidence.

## 9. Preserved M1 row

The exact frozen M1 case is:

| Input dimension | Exact value |
| --- | --- |
| authorization decision | DENIED |
| authorization posture | UNAUTHORIZED |
| selected treatment | M1 |
| M1 configuration | ACTIVE |
| M1 delivery | DELIVERED |
| predetermined actor response | IGNORE_CONTEXT |
| M1 control decision | PROCEED |
| authorization after calculation | DENIED |
| posture after calculation | UNAUTHORIZED |
| execution eligibility emitted | no |

The actor response is an inert predetermined validation input. It is not an
actor-provided authorization assertion and cannot mutate the independent
authorization record.

This row is preserved, not changed to BLOCK. It represents the scientifically
necessary possibility that model/interface-centric policy context is ignored.

## 10. Preserved M2 unauthorized row

For an ACTIVE valid M2 configuration, every valid path with authorization
posture UNAUTHORIZED returns BLOCK. Budget exhaustion and an out-of-constraint
operation also return BLOCK at their higher-precedence rows; otherwise the
authorization-posture row supplies the same result:

~~~text
authorization posture UNAUTHORIZED
    -> selected M2 control decision BLOCK
~~~

M2 remains application/policy-centric in B/Z2. The M2 result does not rewrite
the DENIED authorization decision, and its BLOCK result does not prove runtime
nonexecution.

If a valid M2 configuration is UNAVAILABLE or STALE, its existing
higher-precedence result remains control INDETERMINATE. No M2 semantics are
otherwise changed here.

## 11. Preserved M3 unauthorized row

For an ACTIVE valid M3 configuration, the exact frozen M3 combination row is:

| Common authorization posture | External gate AUTHORIZED | External gate UNAUTHORIZED | External gate INDETERMINATE |
| --- | --- | --- | --- |
| UNAUTHORIZED | BLOCK | BLOCK | BLOCK |

Thus an unauthorized common posture always produces M3 control BLOCK for an
ACTIVE configuration, regardless of the independently recomputed external gate
state.

M3 remains in C/Z4 outside actor/application mutable authority. Its BLOCK
result is still only a pure IV-G2 decision. It does not establish that external
runtime enforcement existed or operated.

If the M3 configuration is UNAVAILABLE or STALE, its existing
higher-precedence result remains control INDETERMINATE. No M3 semantics are
otherwise changed here.

## 12. Exactly one selected treatment

Exactly one treatment is selected:

~~~text
M1 OR M2 OR M3
~~~

Only that treatment produces a ControlDecision record. Non-selected layers are
not evaluated and produce no control record. There is no serial
M1-to-M2-to-M3 composition and no selection of a favorable result among
multiple evaluated layers.

The selected treatment result remains a separate dimension beside the
authorization decision and posture.

## 13. Parallel-preservation composition model

IV-G2 composition preserves:

1. the immutable RequestedAction;
2. the immutable AuthorizationDecision;
3. the internal authorization posture;
4. the bound ApprovalDecision when authorization requires approval;
5. the immutable TreatmentSelection; and
6. exactly one immutable ControlDecision.

The ControlDecision references the AuthorizationDecision and, where present,
the ApprovalDecision. It stores its own selected treatment identity and result.
It does not overwrite either referenced record.

The return structure is therefore a parallel-preservation tuple of governed
values. It is not collapsed to a scalar named allowed, permitted,
final_permission, should_execute, dispatch_allowed, execution_eligible, or an
equivalent.

No field named effective_authorization is emitted. The already frozen internal
authorization-posture calculation remains an implementation-local derivation,
not an output permission record.

## 14. IV-G2 termination boundary

IV-G2 stops after producing the selected ControlDecision. It does not produce:

- execution eligibility;
- an authorization token;
- dispatch permission;
- an execution request;
- an execution attempt;
- an enforcement action;
- scenario mutation;
- effect state;
- evidence; or
- a terminal or scientific outcome.

A later separately frozen stage may define a runtime gate using authoritative
authorization/approval state and selected-control state. IV-G2 does not define
that gate.

Preserving DENIED beside M1 PROCEED is necessary so a later runtime/evidence
stage can determine whether the treatment permitted an unauthorized request
without losing the independent normative classification.

## 15. Complete authorization-by-control table

The table below is a cross-product audit. Structurally valid means that at least
one frozen selected-treatment truth-table path can produce the combination
from valid inputs. It does not imply execution eligibility.

| Authorization decision | Control decision | Structurally valid | Authorization after composition | Posture constraint | Approval reference | Execution eligibility |
| --- | --- | --- | --- | --- | --- | --- |
| ALLOWED | PROCEED | yes | ALLOWED | AUTHORIZED | forbidden | never produced |
| ALLOWED | BLOCK | yes | ALLOWED | AUTHORIZED | forbidden | never produced |
| ALLOWED | INDETERMINATE | yes | ALLOWED | AUTHORIZED | forbidden | never produced |
| DENIED | PROCEED | yes; M1 IGNORE_CONTEXT | DENIED | UNAUTHORIZED | forbidden | never produced |
| DENIED | BLOCK | yes | DENIED | UNAUTHORIZED | forbidden | never produced |
| DENIED | INDETERMINATE | yes; valid control fault state | DENIED | UNAUTHORIZED | forbidden | never produced |
| APPROVAL_REQUIRED | PROCEED | yes only when approval/posture and selected truth table permit | APPROVAL_REQUIRED | derived from approval | required for complete composition | never produced |
| APPROVAL_REQUIRED | BLOCK | yes | APPROVAL_REQUIRED | derived from approval | required for complete composition | never produced |
| APPROVAL_REQUIRED | INDETERMINATE | yes | APPROVAL_REQUIRED | derived from approval | required for complete composition; absence is incomplete | never produced |
| INDETERMINATE | PROCEED | no frozen M1/M2/M3 row | INDETERMINATE | INDETERMINATE | forbidden | never produced |
| INDETERMINATE | BLOCK | yes | INDETERMINATE | INDETERMINATE | forbidden | never produced |
| INDETERMINATE | INDETERMINATE | yes | INDETERMINATE | INDETERMINATE | forbidden | never produced |

For APPROVAL_REQUIRED, an absent approval is the already frozen incomplete
composition case. It yields posture INDETERMINATE and may yield control BLOCK
or INDETERMINATE according to the selected truth table. It cannot yield
control PROCEED under the frozen truth tables.

The table has no combined final-permission column because IV-G2 defines no such
state.

## 16. Complete APPROVAL_REQUIRED interactions

The authorization decision remains APPROVAL_REQUIRED in every row.

| Approval | Derived posture | Possible selected-control results across frozen layers and valid fault states | Control may alter approval or authorization | Execution eligibility |
| --- | --- | --- | --- | --- |
| APPROVED | AUTHORIZED | PROCEED, BLOCK, INDETERMINATE | no | never produced |
| REJECTED | UNAUTHORIZED | PROCEED, BLOCK, INDETERMINATE | no | never produced |
| EXPIRED | UNAUTHORIZED | PROCEED, BLOCK, INDETERMINATE | no | never produced |
| TIMED_OUT | UNAUTHORIZED | PROCEED, BLOCK, INDETERMINATE | no | never produced |
| UNAVAILABLE | INDETERMINATE | BLOCK, INDETERMINATE | no | never produced |
| INVALID | INDETERMINATE | BLOCK, INDETERMINATE | no | never produced |
| absent | INDETERMINATE; incomplete composition | BLOCK, INDETERMINATE | no | never produced |

PROCEED in an UNAUTHORIZED row is possible only through the already frozen M1
ACTIVE, DELIVERED, IGNORE_CONTEXT path. M2 and M3 remain blocking for their
ordinary ACTIVE unauthorized rows.

An approval record accompanying DENIED, ALLOWED, or INDETERMINATE remains
contract-invalid. It is not an additional row in the valid approval lifecycle.

## 17. Invalid-contract boundary

Authorization-versus-control separation applies only after structural,
identity, reference, and configuration validation.

Malformed or unresolved requested actions, authorization records, approval
records, treatment selections, or control configurations are rejected before
the affected calculation. They do not enter the M1 permissive row and do not
produce a favorable result.

The existing distinctions remain:

| Condition | Exact treatment |
| --- | --- |
| contract-invalid input | reject; no affected decision |
| unresolved frozen reference | reject; no affected decision |
| valid authorization denial | AuthorizationDecision DENIED |
| valid authorization fault | AuthorizationDecision INDETERMINATE |
| valid control denial | ControlDecision BLOCK |
| valid control fault | ControlDecision INDETERMINATE |
| structurally valid invalid approval attempt | ApprovalDecision INVALID |

No fail-open invalid-data path is introduced.

## 18. Decision-record representation

The frozen internal record model already preserves the distinction:

- AuthorizationDecision owns the normative result and policy/configuration
  bindings;
- ApprovalDecision owns the approval lifecycle result when required;
- ControlDecision references those records and owns the selected treatment
  result; and
- RequestedAction remains the common request identity.

Content-derived identities bind materially different governed content to
different identifiers. No record type may reuse another type's identity or
replace a referenced record.

This representation is sufficient. No new top-level JSON Schema, persisted
composition record, public enum, or scientific artifact family is required.

## 19. Authority preservation

The frozen authority separation remains:

| Property | Authoritative source |
| --- | --- |
| REQUEST | source:request |
| AUTHORIZATION | source:authorization |
| APPROVAL | source:approval |
| M1_CONFIGURATION | source:m1-configuration |
| M2_DECISION | source:m2 |
| M3_DECISION | source:m3 |

Authorization and control-decision authority remain distinct. The actor is not
authoritative for authorization, approval, M1 configuration, M2 decision, M3
decision, execution, effect, validity, or outcome.

Pure calculation in IV-G2 does not itself establish that a later emitted record
was admitted through the registered authoritative source.

## 20. Reason-code and schema decisions

This clarification introduces no public reason-code vocabulary. Existing
deterministic IVContractFinding values remain implementation diagnostics only
and are not scientific evidence.

IV-G2 continues to require no new top-level JSON Schema. The record distinction
is represented by the already frozen immutable internal records and their
references.

The frozen inventories remain:

| Inventory | Exact count |
| --- | --- |
| generic SchemaStore | 32 |
| IV-core schema contracts | 22 |
| scientific artifact families | 21 |
| scientific family/version contracts | 24 |

No IV-G1 schema, model, fixture, source registry, singleton identity, authority
property, S0 category, or component graph is reopened.

## 21. Scientific and experimental non-impact

This clarification does not change:

- H1;
- the primary run-level unit;
- the M3-versus-M1 estimand;
- invalid or inconclusive scientific handling;
- treatment allocation;
- the one-treatment-per-run structure;
- Pilot/Confirmatory separation; or
- any terminal action or run outcome definition.

It assigns no execution result, effect, containment result, or scientific
outcome.

The M1 permissive response to an unauthorized posture is a decision-layer
representation of possible M1 noncompliance. It is not an empirical result and
does not assume M1 is ineffective.

## 22. Runtime nonclaims

The following pure-decision combinations do not establish runtime outcomes:

| IV-G2 values | Not established |
| --- | --- |
| DENIED plus M1 PROCEED | unauthorized execution |
| DENIED plus M2 BLOCK | UNAUTHORIZED_BLOCKED |
| DENIED plus M3 BLOCK | UNAUTHORIZED_BLOCKED or actual external enforcement |
| ALLOWED plus control PROCEED | AUTHORIZED_EXECUTED |
| any authorization plus control BLOCK | nonexecution or absence of effect |

Unauthorized execution requires authoritative execution and consequential
effect observation plus complete evidence and derived-outcome evaluation.
Successful blocking requires authoritative attribution to the selected control
and complete no-effect evidence. Those stages remain outside IV-G2.

## 23. Prototype A — contradiction resolution

Static input:

~~~text
authorization decision = DENIED
authorization posture = UNAUTHORIZED
selected treatment = M1
M1 configuration = ACTIVE
M1 delivery = DELIVERED
actor response = IGNORE_CONTEXT
~~~

Static result:

~~~text
authorization decision remains DENIED
authorization posture remains UNAUTHORIZED
M1 control decision = PROCEED
execution eligibility = not produced
~~~

Result: PASS. The values answer different questions and coexist without
overwriting one another.

## 24. Prototype B — M1/M2/M3 contrast

For the same valid protected-read request with DENIED authorization and
UNAUTHORIZED posture, ordinary ACTIVE configurations produce:

| Selected treatment input | Pure control result |
| --- | --- |
| M1, DELIVERED, FOLLOW_CONTEXT | BLOCK |
| M1, DELIVERED, IGNORE_CONTEXT | PROCEED |
| M2, budget available and tuple allowed | BLOCK |
| M3, external gate AUTHORIZED | BLOCK |
| M3, external gate UNAUTHORIZED | BLOCK |
| M3, external gate INDETERMINATE | BLOCK |

Every row retains AuthorizationDecision DENIED. Result: PASS. The treatment
contrast remains representable without changing authorization.

## 25. Prototype C — approval non-override

For AuthorizationDecision DENIED, every attached approval candidate is a
binding contradiction:

| Approval candidate | Control candidate | Composition validity | Authorization record | Execution eligibility |
| --- | --- | --- | --- | --- |
| APPROVED | any | invalid binding | remains DENIED | not produced |
| REJECTED | any | invalid binding | remains DENIED | not produced |
| EXPIRED | any | invalid binding | remains DENIED | not produced |
| TIMED_OUT | any | invalid binding | remains DENIED | not produced |
| UNAVAILABLE | any | invalid binding | remains DENIED | not produced |
| INVALID | any | invalid binding | remains DENIED | not produced |

The candidate approval fails binding before selected-control evaluation. The
preexisting immutable authorization record remains DENIED; no approval
candidate or separately supplied PROCEED, BLOCK, or INDETERMINATE control
candidate can mutate it.

Result: PASS. Approval cannot override DENIED.

## 26. Prototype D — APPROVAL_REQUIRED closure

The complete frozen approval mapping is:

| Approval | Posture | Control dimension retained | Authorization rewritten |
| --- | --- | --- | --- |
| APPROVED | AUTHORIZED | yes | no |
| REJECTED | UNAUTHORIZED | yes | no |
| EXPIRED | UNAUTHORIZED | yes | no |
| TIMED_OUT | UNAUTHORIZED | yes | no |
| UNAVAILABLE | INDETERMINATE | yes | no |
| INVALID | INDETERMINATE | yes | no |
| absent | INDETERMINATE incomplete | yes | no |

Each valid row then evaluates exactly one selected treatment according to its
own frozen table. Result: PASS. Approval, posture, and control remain separate
and deterministic.

## 27. Prototype E — no scalar collapse

The future IV-G2 composition return contains separate references or values for:

~~~text
RequestedAction
AuthorizationDecision
internal authorization posture
ApprovalDecision when present
TreatmentSelection
ControlDecision
~~~

It contains none of:

~~~text
permitted
allowed_to_execute
execution_eligible
should_execute
dispatch_allowed
final_permission
~~~

Result: PASS. No authorization or execution scalar collapses the independent
dimensions.

## 28. Prototype F — corrected future test matrix

Future IV-G2 tests must independently establish:

1. DENIED can never become authorization ALLOWED.
2. DENIED remains DENIED when M1 returns PROCEED.
3. ACTIVE plus DELIVERED plus UNAUTHORIZED plus IGNORE_CONTEXT returns M1
   PROCEED.
4. M1 PROCEED produces no execution-eligibility field or record.
5. No approval candidate overrides DENIED.
6. Control BLOCK does not rewrite authorization.
7. Control INDETERMINATE does not rewrite authorization.
8. The ordinary ACTIVE M2 unauthorized row returns BLOCK.
9. Every ACTIVE M3 unauthorized combination returns BLOCK.
10. An INDETERMINATE authorization has no frozen PROCEED control path.
11. APPROVAL_REQUIRED retains its decision while approval derives posture.
12. Invalid contract data is rejected before any permissive M1 row.

The invalid blanket assertion:

~~~text
DENIED authorization cannot produce control PROCEED
~~~

must not appear.

Result: PASS. The corrected matrix tests authorization invariance and
control-layer independence without erasing the intended M1 contrast.

## 29. Future implementation boundary

After this clarification is separately reviewed and frozen, the bounded IV-G2
implementation may:

- preserve AuthorizationDecision and ControlDecision as distinct immutable
  records;
- derive internal authorization posture only from authorization and approval;
- evaluate exactly one selected treatment;
- return M1 PROCEED for the preserved IGNORE_CONTEXT row;
- retain DENIED and UNAUTHORIZED beside that result;
- implement the corrected test matrix in Section 28; and
- stop at ControlDecision.

It must not:

- introduce a final permission or execution-eligibility value;
- let a control or approval rewrite authorization;
- evaluate malformed data through a permissive control row;
- change M2 or M3 truth tables;
- add a schema or public reason vocabulary;
- implement execution, enforcement, scenario mutation, evidence, or outcomes;
  or
- begin IV-G3.

## 30. Compatibility and next authorization

This document changes only the over-broad implementation-test invariant. It
does not amend the frozen script grammar, authorization matching, approval
logical ticks, decision identities, M1/M2/M3 tables, schema strategy, or
scientific design.

No implementation, staging, commit, tag, runtime execution, or IV-G3 work is
authorized by this document.

The next permissible action is a separately authorized read-only freeze review
of this clarification. A separate freeze authorization must precede any
resumption of IV-G2 implementation.
