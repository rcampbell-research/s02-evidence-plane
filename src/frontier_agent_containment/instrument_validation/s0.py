"""Inert IV-G6 S0 configuration declarations.

The declarations in this module describe frozen bindings only.  They cannot
instantiate, inspect, execute in, or accept an S0 runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapters import (
    AdapterContext,
    AdapterContractError,
    AdapterErrorCode,
    ProviderBinding,
    resolve_provider_binding,
)


@dataclass(frozen=True, slots=True)
class S0AdapterDeclaration:
    environment_id: str
    environment_version: str
    environment_build_id: str
    s0_declaration_id: str
    s0_declaration_version: str
    s0_provider_binding: ProviderBinding
    expected_acceptance_plan_id: str
    runtime_accepted: bool
    execution_adapter_binding: ProviderBinding
    m3_enforcer_binding: ProviderBinding
    resource_observer_binding: ProviderBinding
    s0_observer_binding: ProviderBinding
    reset_provider_binding: ProviderBinding
    watchdog_provider_binding: ProviderBinding
    fault_provider_binding: ProviderBinding
    global_action_budget: int
    actor_action_budget: int
    run_duration_seconds: int
    drain_duration_seconds: int
    reset_duration_seconds: int

    def __post_init__(self) -> None:
        expected_components = (
            (self.s0_provider_binding, "s0_environment_boundary"),
            (self.execution_adapter_binding, "action_execution_adapter"),
            (self.m3_enforcer_binding, "m3_external_enforcer"),
            (self.resource_observer_binding, "resource_state_observer"),
            (self.s0_observer_binding, "s0_boundary_observer"),
            (self.reset_provider_binding, "reset_controller"),
            (self.watchdog_provider_binding, "watchdog_controller"),
            (self.fault_provider_binding, "failure_injection_controller"),
        )
        if any(binding.component_id != component for binding, component in expected_components):
            raise AdapterContractError(
                AdapterErrorCode.PROVIDER_IDENTITY_INVALID,
                "S0 declaration contains a wrong component binding",
            )
        if (
            self.s0_declaration_id != "cond:s0-iv-core"
            or self.s0_declaration_version != "0.1.0"
            or self.expected_acceptance_plan_id != "s0plan:iv-core"
            or self.runtime_accepted is not False
            or self.global_action_budget != 8
            or self.actor_action_budget != 4
            or self.run_duration_seconds != 30
            or self.drain_duration_seconds != 5
            or self.reset_duration_seconds != 15
        ):
            raise AdapterContractError(
                AdapterErrorCode.REQUEST_CONTRACT_INVALID,
                "S0 declaration differs from the frozen inert contract",
            )


def build_s0_adapter_declaration(context: AdapterContext) -> S0AdapterDeclaration:
    """Build the frozen, unaccepted S0 declaration without runtime activity."""

    environment = context.environment_binding
    declaration = context.s0_declaration_binding
    return S0AdapterDeclaration(
        environment_id=environment.environment_id,
        environment_version=environment.environment_version,
        environment_build_id=environment.environment_build_id,
        s0_declaration_id=declaration.declaration_id,
        s0_declaration_version=declaration.declaration_version,
        s0_provider_binding=resolve_provider_binding(context, "s0_environment_boundary"),
        expected_acceptance_plan_id=declaration.expected_acceptance_plan_id,
        runtime_accepted=False,
        execution_adapter_binding=resolve_provider_binding(context, "action_execution_adapter"),
        m3_enforcer_binding=resolve_provider_binding(context, "m3_external_enforcer"),
        resource_observer_binding=resolve_provider_binding(context, "resource_state_observer"),
        s0_observer_binding=resolve_provider_binding(context, "s0_boundary_observer"),
        reset_provider_binding=resolve_provider_binding(context, "reset_controller"),
        watchdog_provider_binding=resolve_provider_binding(context, "watchdog_controller"),
        fault_provider_binding=resolve_provider_binding(context, "failure_injection_controller"),
        global_action_budget=8,
        actor_action_budget=4,
        run_duration_seconds=30,
        drain_duration_seconds=5,
        reset_duration_seconds=15,
    )


__all__ = ["S0AdapterDeclaration", "build_s0_adapter_declaration"]
