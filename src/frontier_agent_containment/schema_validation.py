"""Strict, network-independent JSON Schema validation primitives.

This Stage 1 foundation implements the strictness and testability requirements
of the frozen Implementation Contract v0.1 without adding scientific contract
semantics. It does not coerce, repair, migrate, or rewrite inputs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, TypeAlias

from jsonschema import Draft202012Validator


JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)
Schema: TypeAlias = Mapping[str, Any]

VALIDATOR_CLASS: Final = Draft202012Validator
"""The sole JSON Schema dialect validator used by this foundation."""


class ExternalSchemaReferenceError(ValueError):
    """Raised when a schema requests resolution outside its own document."""


class DuplicateJsonKeyError(ValueError):
    """Raised when a JSON object repeats a member name."""

    def __init__(self, key: str) -> None:
        super().__init__(f"duplicate JSON object member: {key!r}")
        self.key = key


def load_json(path: str | Path) -> JsonValue:
    """Load one JSON document without coercion, repair, or error suppression.

    Malformed JSON raises :class:`json.JSONDecodeError`; filesystem and encoding
    failures retain their standard exceptions. Duplicate object members raise
    :class:`DuplicateJsonKeyError` instead of being silently overwritten. These
    are intentionally distinct from schema validation errors raised by
    :func:`validate_instance`.
    """

    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=_object_without_duplicate_keys)


def check_draft_2020_12_schema(schema: Schema) -> None:
    """Check that *schema* is valid Draft 2020-12 and locally resolvable.

    External and remote references are rejected before validation so schema
    checking and instance validation cannot trigger network retrieval.
    Invalid schema definitions otherwise raise ``jsonschema.SchemaError``.
    """

    _reject_external_references(schema)
    VALIDATOR_CLASS.check_schema(schema)


def validate_instance(instance: JsonValue, schema: Schema) -> None:
    """Validate *instance* without modifying it or the supplied *schema*.

    The schema is checked first. An invalid instance raises
    ``jsonschema.ValidationError``; success returns ``None``.
    """

    check_draft_2020_12_schema(schema)
    VALIDATOR_CLASS(schema).validate(instance)


def _reject_external_references(node: Any) -> None:
    """Reject references requiring resolution beyond the supplied document."""

    if isinstance(node, Mapping):
        for key, value in node.items():
            if key in {"$ref", "$dynamicRef"} and isinstance(value, str):
                if not value.startswith("#"):
                    raise ExternalSchemaReferenceError(
                        f"external schema reference is not supported: {value!r}"
                    )
            _reject_external_references(value)
    elif isinstance(node, list):
        for value in node:
            _reject_external_references(value)


def _object_without_duplicate_keys(pairs: list[tuple[str, JsonValue]]) -> JsonValue:
    """Build a JSON object while rejecting ambiguous repeated member names."""

    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(key)
        result[key] = value
    return result
