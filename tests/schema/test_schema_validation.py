"""Stage 1 tests for strict, network-independent schema validation."""

from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from frontier_agent_containment.schema_validation import (
    VALIDATOR_CLASS,
    ExternalSchemaReferenceError,
    check_draft_2020_12_schema,
    load_json,
    validate_instance,
)


def strict_object_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
        "additionalProperties": False,
    }


def test_valid_draft_2020_12_schema_passes_check() -> None:
    check_draft_2020_12_schema(strict_object_schema())


def test_invalid_schema_definition_is_rejected() -> None:
    invalid_schema = {"type": 42}

    with pytest.raises(SchemaError):
        check_draft_2020_12_schema(invalid_schema)


def test_valid_instance_passes_validation() -> None:
    validate_instance({"count": 1}, strict_object_schema())


def test_wrong_json_type_fails_validation() -> None:
    with pytest.raises(ValidationError):
        validate_instance([1], strict_object_schema())


def test_missing_required_field_fails_validation() -> None:
    with pytest.raises(ValidationError):
        validate_instance({}, strict_object_schema())


def test_unknown_field_fails_when_schema_is_strict() -> None:
    with pytest.raises(ValidationError):
        validate_instance({"count": 1, "unexpected": True}, strict_object_schema())


def test_string_is_not_coerced_to_integer() -> None:
    instance = {"count": "1"}

    with pytest.raises(ValidationError):
        validate_instance(instance, strict_object_schema())

    assert instance == {"count": "1"}


def test_malformed_json_is_distinct_from_schema_failure(tmp_path) -> None:
    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text('{"count":', encoding="utf-8")
    wrong_type_path = tmp_path / "wrong-type.json"
    wrong_type_path.write_text('{"count": "1"}', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_json(malformed_path)

    parsed_document = load_json(wrong_type_path)
    with pytest.raises(ValidationError):
        validate_instance(parsed_document, strict_object_schema())


def test_validation_does_not_rewrite_input_instance() -> None:
    instance = {"count": 1}
    original = copy.deepcopy(instance)

    validate_instance(instance, strict_object_schema())

    assert instance == original


def test_draft_2020_12_validator_is_used() -> None:
    assert VALIDATOR_CLASS is Draft202012Validator

    tuple_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "array",
        "prefixItems": [{"type": "integer"}],
        "items": False,
    }
    validate_instance([1], tuple_schema)
    with pytest.raises(ValidationError):
        validate_instance([1, 2], tuple_schema)


def test_external_schema_reference_is_rejected_without_resolution() -> None:
    schema = {"$ref": "https://example.invalid/remote-schema.json"}

    with pytest.raises(ExternalSchemaReferenceError):
        check_draft_2020_12_schema(schema)
