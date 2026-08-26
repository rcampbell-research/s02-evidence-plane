"""Portable canonical-content and forensic-byte integrity primitives.

Canonical JSON serialization follows the frozen Integrity & Reproducibility
Specification v0.1 by delegating RFC 8785 behavior to the pinned ``rfc8785``
implementation. Digests identify exact content under their declared procedure;
they do not authenticate a producer or prove truth, completeness, immutability,
authorization, historical existence, or system security.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, TypeAlias

import rfc8785


JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


class IntegrityError(Exception):
    """Base class for project-level integrity primitive failures."""


class UnsupportedJsonTypeError(IntegrityError, TypeError):
    """Raised when a value is outside the strict Python JSON input domain."""


class JsonCanonicalizationError(IntegrityError, ValueError):
    """Raised when an otherwise JSON-shaped value is outside the JCS domain."""


def canonicalize_json(value: JsonValue) -> bytes:
    """Return RFC 8785 JCS UTF-8 bytes for one strict JSON-domain value.

    The accepted Python values are exactly those produced by a normal strict
    JSON parser: ``dict``, ``list``, ``str``, ``int``, ``float``, ``bool``, and
    ``None``. Containers are checked recursively without mutation or coercion.
    Duplicate object names must already have been rejected while parsing source
    JSON because an in-memory ``dict`` cannot retain that ambiguity.
    """

    _validate_json_domain(value)
    try:
        return rfc8785.dumps(value)
    except rfc8785.CanonicalizationError as exc:
        raise JsonCanonicalizationError(str(exc)) from exc


def canonical_sha256(value: JsonValue) -> str:
    """Return a lowercase SHA-256 integrity identifier for canonical JSON."""

    canonical_bytes = canonicalize_json(value)
    return _format_sha256(canonical_bytes)


def forensic_sha256_bytes(data: bytes) -> str:
    """Return a SHA-256 integrity identifier over the exact supplied bytes.

    This function does not parse, decode, normalize, or canonicalize *data*.
    A forensic byte digest is not an RFC 8785 canonical artifact digest.
    """

    if type(data) is not bytes:
        raise TypeError("forensic byte digest input must be bytes")
    return _format_sha256(data)


def _validate_json_domain(value: Any, *, path: str = "$") -> None:
    """Reject values that a strict JSON parser would not produce."""

    value_type = type(value)

    if value is None or value_type in {bool, int, str}:
        return

    if value_type is float:
        if not math.isfinite(value):
            raise JsonCanonicalizationError(
                f"non-finite JSON number at {path} is not representable in JCS"
            )
        return

    if value_type is list:
        for index, item in enumerate(value):
            _validate_json_domain(item, path=f"{path}[{index}]")
        return

    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise UnsupportedJsonTypeError(
                    f"JSON object key at {path} must be an exact str, "
                    f"not {type(key).__name__}"
                )
            _validate_json_domain(item, path=f"{path}[{key!r}]")
        return

    raise UnsupportedJsonTypeError(
        f"unsupported JSON value at {path}: {value_type.__name__}"
    )


def _format_sha256(data: bytes) -> str:
    """Format the frozen v0.1 SHA-256 integrity identifier."""

    return "sha256:" + hashlib.sha256(data).hexdigest()
