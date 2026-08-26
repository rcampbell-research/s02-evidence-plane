"""Strict, network-independent JSON Schema validation primitives.

This foundation implements the strictness and testability requirements of the
frozen Implementation Contract v0.1. It supports only explicitly supplied
project schemas and never coerces, repairs, migrates, or rewrites inputs.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Final, TypeAlias
from urllib.parse import urljoin

from jsonschema import Draft202012Validator, RefResolver


JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)
Schema: TypeAlias = Mapping[str, Any]
SchemaStore: TypeAlias = Mapping[str, Schema]

PROJECT_SCHEMA_ID_PREFIX: Final = "urn:frontier-agent-containment:schema:"

VALIDATOR_CLASS: Final = Draft202012Validator
"""The sole JSON Schema dialect validator used by this foundation."""


class ExternalSchemaReferenceError(ValueError):
    """Raised when a schema requests uncontrolled external resolution."""


class UnknownSchemaReferenceError(ValueError):
    """Raised when a project schema reference is absent from the local store."""


class SchemaStoreError(ValueError):
    """Raised when a supplied local schema store is malformed."""


class DuplicateSchemaIdError(SchemaStoreError):
    """Raised when local schema documents declare the same schema identifier."""


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


def load_schema_store(paths: Iterable[str | Path]) -> dict[str, Schema]:
    """Load and validate an explicit collection of project schema documents.

    Every document must be a JSON object with a unique project ``$id``. All
    references must be local fragments or resolve to another schema in this
    exact collection. No search path, URI retrieval, or network fallback is
    used.
    """

    store: dict[str, Schema] = {}
    for path in paths:
        document = load_json(path)
        if not isinstance(document, Mapping):
            raise SchemaStoreError(f"schema document is not an object: {path}")
        schema_id = _project_schema_id(document, source=str(path))
        if schema_id in store:
            raise DuplicateSchemaIdError(f"duplicate schema $id: {schema_id!r}")
        VALIDATOR_CLASS.check_schema(document)
        store[schema_id] = document

    _check_store_references(store)
    return store


def check_draft_2020_12_schema(
    schema: Schema, *, schema_store: SchemaStore | None = None
) -> None:
    """Check that *schema* is valid Draft 2020-12 and locally resolvable.

    References may use local fragments or project URNs present in the explicit
    *schema_store*. External and missing project references are rejected before
    instance validation, so resolution cannot trigger network retrieval.
    Invalid schema definitions otherwise raise ``jsonschema.SchemaError``.
    """

    store = _prepare_schema_store(schema_store)
    VALIDATOR_CLASS.check_schema(schema)
    _check_reference_policy(schema, store)


def validate_instance(
    instance: JsonValue,
    schema: Schema,
    *,
    schema_store: SchemaStore | None = None,
) -> None:
    """Validate *instance* without modifying it or the supplied *schema*.

    The schema is checked first. An invalid instance raises
    ``jsonschema.ValidationError``; success returns ``None``.
    """

    store = _prepare_schema_store(schema_store)
    VALIDATOR_CLASS.check_schema(schema)
    _check_reference_policy(schema, store)
    resolver = RefResolver.from_schema(
        schema,
        store=dict(store),
        handlers={
            "file": _deny_uri_retrieval,
            "ftp": _deny_uri_retrieval,
            "http": _deny_uri_retrieval,
            "https": _deny_uri_retrieval,
            "urn": _deny_uri_retrieval,
        },
        urljoin_cache=_join_schema_uri,
    )
    VALIDATOR_CLASS(schema, resolver=resolver).validate(instance)


def _prepare_schema_store(schema_store: SchemaStore | None) -> dict[str, Schema]:
    """Validate a caller-supplied in-memory store without changing it."""

    if schema_store is None:
        return {}

    prepared: dict[str, Schema] = {}
    for declared_id, schema in schema_store.items():
        if not isinstance(schema, Mapping):
            raise SchemaStoreError(
                f"schema store value for {declared_id!r} is not an object"
            )
        schema_id = _project_schema_id(schema, source=f"store key {declared_id!r}")
        if schema_id in prepared:
            raise DuplicateSchemaIdError(f"duplicate schema $id: {schema_id!r}")
        if declared_id != schema_id:
            raise SchemaStoreError(
                f"schema store key {declared_id!r} does not match $id {schema_id!r}"
            )
        VALIDATOR_CLASS.check_schema(schema)
        prepared[schema_id] = schema

    _check_store_references(prepared)
    return prepared


def _project_schema_id(schema: Schema, *, source: str) -> str:
    """Return a valid project ``$id`` from one store document."""

    schema_id = schema.get("$id")
    if not isinstance(schema_id, str) or not schema_id.startswith(
        PROJECT_SCHEMA_ID_PREFIX
    ):
        raise SchemaStoreError(f"schema from {source} lacks a valid project $id")
    return schema_id


def _check_store_references(store: SchemaStore) -> None:
    """Check every stored schema against the complete explicit store."""

    for schema in store.values():
        _check_reference_policy(schema, store)


def _check_reference_policy(node: Any, schema_store: SchemaStore) -> None:
    """Allow only document fragments and known project-schema URNs."""

    if isinstance(node, Mapping):
        for key, value in node.items():
            if key == "$id" and isinstance(value, str):
                _check_schema_identifier(value)
            elif key in {"$ref", "$dynamicRef"} and isinstance(value, str):
                _check_reference(value, schema_store)
            _check_reference_policy(value, schema_store)
    elif isinstance(node, list):
        for value in node:
            _check_reference_policy(value, schema_store)


def _check_schema_identifier(schema_id: str) -> None:
    """Reject schema bases that could redirect fragment resolution externally."""

    if not schema_id.startswith(PROJECT_SCHEMA_ID_PREFIX):
        raise ExternalSchemaReferenceError(
            f"external schema identifier is not supported: {schema_id!r}"
        )


def _check_reference(reference: str, schema_store: SchemaStore) -> None:
    """Validate one schema reference without attempting to resolve it."""

    if reference.startswith("#"):
        return
    if reference.startswith(PROJECT_SCHEMA_ID_PREFIX):
        schema_id = reference.split("#", 1)[0]
        if schema_id not in schema_store:
            raise UnknownSchemaReferenceError(
                f"project schema reference is not in the local store: {reference!r}"
            )
        return
    raise ExternalSchemaReferenceError(
        f"external schema reference is not supported: {reference!r}"
    )


def _join_schema_uri(base_uri: str, reference: str) -> str:
    """Join references while preserving the base of opaque project URNs.

    Python's standard URI join discards an opaque URN when joining a fragment.
    The installed resolver delegates URI joining, so this adapter keeps nested
    common-schema fragments scoped to the project schema that declared them.
    """

    if reference.startswith(PROJECT_SCHEMA_ID_PREFIX):
        return reference
    if reference.startswith("#") and base_uri.startswith(PROJECT_SCHEMA_ID_PREFIX):
        return base_uri.split("#", 1)[0] + reference
    return urljoin(base_uri, reference)


def _deny_uri_retrieval(uri: str) -> Any:
    """Defensive resolver handler that makes every retrieval attempt fail."""

    raise ExternalSchemaReferenceError(f"schema URI retrieval is disabled: {uri!r}")


def _object_without_duplicate_keys(pairs: list[tuple[str, JsonValue]]) -> JsonValue:
    """Build a JSON object while rejecting ambiguous repeated member names."""

    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(key)
        result[key] = value
    return result
