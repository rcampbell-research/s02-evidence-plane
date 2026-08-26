"""Stage 12B tests for RFC 8785 canonicalization and SHA-256 primitives."""

from __future__ import annotations

from copy import deepcopy
import json
import re

import pytest
import rfc8785

from frontier_agent_containment.integrity import (
    JsonCanonicalizationError,
    UnsupportedJsonTypeError,
    canonical_sha256,
    canonicalize_json,
    forensic_sha256_bytes,
)
from frontier_agent_containment.schema_validation import (
    DuplicateJsonKeyError,
    load_json,
)


# The number, string-escaping, and UTF-16 ordering expectations below are
# transcribed or reduced from RFC 8785 Sections 3.2.2 and 3.2.3. All expected
# canonical bytes are fixed constants; none is generated through rfc8785 or the
# project functions under test.
UTF16_ORDER_INPUT = {
    "\u20ac": "Euro Sign",
    "\r": "Carriage Return",
    "\ufb33": "Hebrew Letter Dalet With Dagesh",
    "1": "One",
    "\U0001f600": "Emoji: Grinning Face",
    "\u0080": "Control",
    "\u00f6": "Latin Small Letter O With Diaeresis",
}

UTF16_ORDER_EXPECTED = (
    b'{"\\r":"Carriage Return","1":"One","\xc2\x80":"Control",'
    b'"\xc3\xb6":"Latin Small Letter O With Diaeresis",'
    b'"\xe2\x82\xac":"Euro Sign",'
    b'"\xf0\x9f\x98\x80":"Emoji: Grinning Face",'
    b'"\xef\xac\xb3":"Hebrew Letter Dalet With Dagesh"}'
)

CANONICAL_VECTORS = [
    ("empty-object", {}, b"{}"),
    ("empty-array", [], b"[]"),
    ("null", None, b"null"),
    ("true", True, b"true"),
    ("false", False, b"false"),
    ("plain-string", "hello", b'"hello"'),
    ("property-reordering", {"b": 1, "a": 2}, b'{"a":2,"b":1}'),
    (
        "nested-object",
        {"z": {"b": 2, "a": 1}, "a": [3, {"d": 4, "c": 5}]},
        b'{"a":[3,{"c":5,"d":4}],"z":{"a":1,"b":2}}',
    ),
    ("nested-array", [3, [2, 1], {"b": 2, "a": 1}], b'[3,[2,1],{"a":1,"b":2}]'),
    ("integer", 42, b"42"),
    ("negative-integer", -42, b"-42"),
    ("zero", 0, b"0"),
    ("finite-float", 4.5, b"4.5"),
    ("large-exponent", 1e30, b"1e+30"),
    ("decimal-small", 2e-3, b"0.002"),
    ("small-exponent", 1e-27, b"1e-27"),
    ("binary64-rounding", 333333333.33333329, b"333333333.3333333"),
    ("escaped-control", "\u000f\n\"\\/", b'"\\u000f\\n\\"\\\\/"'),
    ("unicode", "\u20ac\U0001f600", b'"\xe2\x82\xac\xf0\x9f\x98\x80"'),
    ("utf16-order", UTF16_ORDER_INPUT, UTF16_ORDER_EXPECTED),
]


# SHA-256 constants were independently calculated over the adjacent fixed byte
# strings with Python's standard hashlib, never with canonical_sha256.
DIGEST_VECTORS = [
    (
        "empty-object",
        {},
        "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    ),
    (
        "ordered-object",
        {"b": 1, "a": 2},
        "sha256:d3626ac30a87e6f7a6428233b3c68299976865fa5508e4267c5415c76af7a772",
    ),
    (
        "changed-a1",
        {"a": 1},
        "sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862",
    ),
    (
        "changed-a2",
        {"a": 2},
        "sha256:7e8059f495589fcd981232cc11d00b00da3802c01d688fa1cf1f6bed6e5bb33c",
    ),
    (
        "nested",
        {"z": {"b": 2, "a": 1}, "a": [3, {"d": 4, "c": 5}]},
        "sha256:3eb62673a009296eaa1a2a988d9d718821527c6de09be527dd72f2c237edd98c",
    ),
    (
        "utf16-order",
        UTF16_ORDER_INPUT,
        "sha256:5e321556d22018a9656991a9e94f77ec175fa193e52a2429d312f8419ec8b08c",
    ),
]


FORENSIC_VECTORS = [
    (
        "valid-json",
        b'{"a":1}',
        "sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862",
    ),
    (
        "formatted-json",
        b'{ "a": 1 }',
        "sha256:efc6fbbe835f02996e070d9b3f37ffc4153f8ed11590fbf555bff7021d271fe9",
    ),
    (
        "malformed-json",
        b'{"a":',
        "sha256:ffb38b22ee3e0ca90325ebce953a9846990f292faf44c50498771602e31cb61f",
    ),
    (
        "duplicate-key-json",
        b'{"a":1,"a":2}',
        "sha256:1c53ee0df7b12fd4d65b976120c7fa6b847dc41dffd7f0331c3237a1ceab1756",
    ),
    (
        "binary",
        b"\x00\xff\x10",
        "sha256:2da45f2cd1f9c8e69a67abf7a6b26c282533d0a7686787a9533265418680d4d2",
    ),
]


@pytest.mark.parametrize(
    ("_name", "value", "expected"),
    CANONICAL_VECTORS,
    ids=[item[0] for item in CANONICAL_VECTORS],
)
def test_fixed_canonicalization_vectors(_name, value, expected):
    assert canonicalize_json(value) == expected


@pytest.mark.parametrize(
    ("_name", "value", "expected"),
    DIGEST_VECTORS,
    ids=[item[0] for item in DIGEST_VECTORS],
)
def test_fixed_canonical_digest_vectors(_name, value, expected):
    assert canonical_sha256(value) == expected
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", expected)


@pytest.mark.parametrize(
    ("_name", "data", "expected"),
    FORENSIC_VECTORS,
    ids=[item[0] for item in FORENSIC_VECTORS],
)
def test_fixed_forensic_digest_vectors(_name, data, expected):
    assert forensic_sha256_bytes(data) == expected


def test_utf16_property_order_differs_from_python_codepoint_order():
    python_order = sorted(UTF16_ORDER_INPUT)
    assert python_order.index("\ufb33") < python_order.index("\U0001f600")
    canonical = canonicalize_json(UTF16_ORDER_INPUT)
    assert canonical == UTF16_ORDER_EXPECTED
    assert canonical.index("\U0001f600".encode()) < canonical.index("\ufb33".encode())


def test_unicode_is_preserved_without_normalization():
    composed = canonicalize_json("\u00e9")
    decomposed = canonicalize_json("e\u0301")
    assert composed == b'"\xc3\xa9"'
    assert decomposed == b'"e\xcc\x81"'
    assert composed != decomposed


@pytest.mark.parametrize(
    "value",
    [
        ("tuple", 1),
        {"set"},
        b"bytes",
        bytearray(b"bytes"),
        object(),
    ],
    ids=["tuple", "set", "bytes", "bytearray", "object"],
)
def test_non_json_python_values_are_rejected(value):
    with pytest.raises(UnsupportedJsonTypeError):
        canonicalize_json(value)


def test_nested_unsupported_value_is_rejected_without_coercion():
    value = {"items": [1, (2, 3)]}
    with pytest.raises(UnsupportedJsonTypeError, match=r"\$\['items'\]\[1\]"):
        canonicalize_json(value)


def test_non_string_object_key_is_rejected():
    with pytest.raises(UnsupportedJsonTypeError, match="key"):
        canonicalize_json({1: "value"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_numbers_are_rejected(value):
    with pytest.raises(JsonCanonicalizationError, match="non-finite"):
        canonicalize_json(value)


@pytest.mark.parametrize("value", [2**53, -(2**53)])
def test_out_of_domain_integers_are_rejected_by_dependency_boundary(value):
    with pytest.raises(JsonCanonicalizationError) as captured:
        canonicalize_json(value)
    assert isinstance(captured.value.__cause__, rfc8785.IntegerDomainError)


@pytest.mark.parametrize("value", [(2**53) - 1, -(2**53) + 1])
def test_safe_integer_boundaries_are_accepted(value):
    assert canonicalize_json(value) == str(value).encode("ascii")


def test_invalid_unicode_is_reported_through_project_error_boundary():
    with pytest.raises(JsonCanonicalizationError) as captured:
        canonicalize_json("\ud800")
    assert isinstance(captured.value.__cause__, rfc8785.CanonicalizationError)


def test_dependency_tuple_acceptance_is_narrowed_by_project_wrapper():
    assert rfc8785.dumps(("value", 1)) == b'["value",1]'
    with pytest.raises(UnsupportedJsonTypeError):
        canonicalize_json(("value", 1))


@pytest.mark.parametrize("value", [bytearray(b"x"), memoryview(b"x"), "x"])
def test_forensic_digest_is_strictly_bytes_only(value):
    with pytest.raises(TypeError, match="must be bytes"):
        forensic_sha256_bytes(value)


def test_forensic_digest_preserves_exact_raw_formatting():
    compact = forensic_sha256_bytes(b'{"a":1}')
    formatted = forensic_sha256_bytes(b'{ "a": 1 }')
    assert compact != formatted


def test_canonicalization_and_digest_do_not_mutate_nested_input():
    value = {
        "unicode": "e\u0301",
        "items": [{"z": 2, "a": 1}, [True, None, 4.5]],
    }
    original = deepcopy(value)
    canonicalize_json(value)
    canonical_sha256(value)
    assert value == original


def test_repeated_calls_are_deterministic():
    value = {"z": [3, 2, 1], "a": {"b": 2, "a": 1}}
    canonical_results = [canonicalize_json(value) for _ in range(5)]
    digest_results = [canonical_sha256(value) for _ in range(5)]
    assert canonical_results == [canonical_results[0]] * 5
    assert digest_results == [digest_results[0]] * 5


def test_changed_content_has_fixed_distinct_digests():
    first = canonical_sha256({"a": 1})
    second = canonical_sha256({"a": 2})
    assert first == DIGEST_VECTORS[2][2]
    assert second == DIGEST_VECTORS[3][2]
    assert first != second


def test_differently_formatted_strict_json_has_same_canonical_content(tmp_path):
    compact_path = tmp_path / "compact.json"
    formatted_path = tmp_path / "formatted.json"
    compact_path.write_bytes(b'{"b":2,"a":[1,2]}')
    formatted_path.write_bytes(b'{\n  "a": [1, 2],\n  "b": 2\n}\n')

    compact = load_json(compact_path)
    formatted = load_json(formatted_path)
    assert canonicalize_json(compact) == b'{"a":[1,2],"b":2}'
    assert canonicalize_json(compact) == canonicalize_json(formatted)
    assert canonical_sha256(compact) == canonical_sha256(formatted)


def test_duplicate_key_json_is_rejected_before_canonicalization(tmp_path):
    raw = b'{"a":1,"a":2}'
    path = tmp_path / "duplicate.json"
    path.write_bytes(raw)
    with pytest.raises(DuplicateJsonKeyError):
        load_json(path)
    assert forensic_sha256_bytes(raw) == FORENSIC_VECTORS[3][2]


def test_malformed_json_is_rejected_before_canonicalization(tmp_path):
    raw = b'{"a":'
    path = tmp_path / "malformed.json"
    path.write_bytes(raw)
    with pytest.raises(json.JSONDecodeError):
        load_json(path)
    assert forensic_sha256_bytes(raw) == FORENSIC_VECTORS[2][2]


def test_repeated_array_values_remain_valid(tmp_path):
    path = tmp_path / "repeated-array.json"
    path.write_bytes(b'{"values":["same","same"]}')
    value = load_json(path)
    assert canonicalize_json(value) == b'{"values":["same","same"]}'


def test_paths_do_not_enter_content_identity(tmp_path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "moved.json"
    raw = b'{"a":1}'
    first_path.write_bytes(raw)
    second_path.write_bytes(raw)
    assert canonical_sha256(load_json(first_path)) == canonical_sha256(
        load_json(second_path)
    )
