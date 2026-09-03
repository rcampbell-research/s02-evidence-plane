"""Inert IV-G6 observer declarations.

These immutable projections bind later observer providers to their existing
local source channels.  They perform no observation or collection.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapters import (
    AdapterContext,
    AdapterContractError,
    AdapterErrorCode,
    LocalSourceChannelBinding,
    ProviderBinding,
    resolve_provider_binding,
    resolve_source_channel_binding,
)


@dataclass(frozen=True, slots=True)
class ResourceObserverDeclaration:
    provider_binding: ProviderBinding
    source_channel_binding: LocalSourceChannelBinding

    def __post_init__(self) -> None:
        if self.provider_binding.component_id != "resource_state_observer":
            raise AdapterContractError(
                AdapterErrorCode.PROVIDER_IDENTITY_INVALID,
                "resource observer declaration has the wrong provider",
            )
        source = self.source_channel_binding
        if (
            source.source_component_id != "resource_state_observer"
            or source.source_registration_id != "source:resource"
            or source.dedicated_local_channel_id != "channel_resource"
            or source.authoritative_properties
            != ("CONSEQUENTIAL_EFFECT", "BENIGN_TASK_OBSERVATION", "RESET_STATE")
        ):
            raise AdapterContractError(
                AdapterErrorCode.PROVIDER_CHANNEL_INVALID,
                "resource observer declaration has the wrong source binding",
            )


@dataclass(frozen=True, slots=True)
class S0ObserverDeclaration:
    provider_binding: ProviderBinding
    source_channel_binding: LocalSourceChannelBinding
    authoritative_property: str

    def __post_init__(self) -> None:
        if self.provider_binding.component_id != "s0_boundary_observer":
            raise AdapterContractError(
                AdapterErrorCode.PROVIDER_IDENTITY_INVALID,
                "S0 observer declaration has the wrong provider",
            )
        source = self.source_channel_binding
        if (
            source.source_component_id != "s0_boundary_observer"
            or source.source_registration_id != "source:s0"
            or source.dedicated_local_channel_id != "channel_s0"
            or source.authoritative_properties != ("S0_STATE",)
            or self.authoritative_property != "S0_STATE"
        ):
            raise AdapterContractError(
                AdapterErrorCode.PROVIDER_CHANNEL_INVALID,
                "S0 observer declaration has the wrong source binding",
            )


def build_resource_observer_declaration(
    context: AdapterContext,
) -> ResourceObserverDeclaration:
    """Build an inert resource-observer declaration from explicit context."""

    return ResourceObserverDeclaration(
        resolve_provider_binding(context, "resource_state_observer"),
        resolve_source_channel_binding(context, "source:resource"),
    )


def build_s0_observer_declaration(context: AdapterContext) -> S0ObserverDeclaration:
    """Build an inert S0-observer declaration without observing S0."""

    return S0ObserverDeclaration(
        resolve_provider_binding(context, "s0_boundary_observer"),
        resolve_source_channel_binding(context, "source:s0"),
        "S0_STATE",
    )


__all__ = [
    "ResourceObserverDeclaration",
    "S0ObserverDeclaration",
    "build_resource_observer_declaration",
    "build_s0_observer_declaration",
]
