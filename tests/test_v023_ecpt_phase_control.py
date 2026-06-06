from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.adapters.domain import (
    verify_ecpt_bridge_reserve,
    verify_ecpt_domain_abstraction,
    verify_ecpt_execution_policy,
    verify_ecpt_proxy_target_contract,
    verify_ecpt_speculative_channel_repair,
    verify_ecpt_trace_diagnostic_projection,
)
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecpt import (
    ASIProxyTargetContract,
    CapabilityHypergraph,
    CapabilityPacket,
    CapabilityStateVector,
    ConstraintFrame,
    PhaseControlAction,
    PhaseControlObjective,
    PhaseControlState,
    build_phase_control_plan,
)
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def _state(*, hard_live: bool = True) -> PhaseControlState:
    return PhaseControlState(
        state_id="state",
        graph=CapabilityHypergraph(
            nodes={"compute", "models"},
            seed_mass={"compute": 1.0},
        ),
        state_vector=CapabilityStateVector(
            packets=[CapabilityPacket(packet_id="seed", coordinates={"compute": 1.0})],
        ),
        constraint_frame=ConstraintFrame(hard_gates={"safe": hard_live}),
        present_obligations=["obligation:baseline-safety"],
        budgets={"compute": 1.0},
    )


def _objective() -> PhaseControlObjective:
    return PhaseControlObjective(
        objective_id="objective",
        target=ASIProxyTargetContract(
            target_id="target",
            target_nodes=["phase-transition-proxy"],
            minimum_proxy_mass=0.01,
            required_obligations=["obligation:baseline-safety"],
        ),
        residual_budget=0.2,
        risk_tolerance=0.1,
    )


def _action(action_id: str = "activate") -> PhaseControlAction:
    return PhaseControlAction(
        action_id=action_id,
        source_nodes=["compute"],
        target_node="phase-transition-proxy",
        activation_delta=0.8,
        burden_delta=0.05,
        residual_charge=0.01,
        risk_charge=0.02,
        resource_cost={"compute": 0.1},
        verifier_routes=["ecpt.adapters.proxy.verify_target_contract"],
        preconditions=["compute"],
        required_obligations=["obligation:baseline-safety"],
    )


def test_phase_control_plan_is_deterministic_and_never_settles() -> None:
    first = build_phase_control_plan(_state(), _objective(), [_action("b"), _action("a")])
    second = build_phase_control_plan(_state(), _objective(), [_action("b"), _action("a")])
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.plan.accepted
    assert first.plan.selected_actions[0].action_id == "a"
    assert first.plan.finite_proxy_gain_total > 0
    assert not first.plan.settled
    assert first.plan.status == "provisional"
    assert "proxy-target-grounding-proof" in first.plan.missing_obligations


def test_phase_control_hard_gate_and_budget_debt_are_diagnostic() -> None:
    report = build_phase_control_plan(
        _state(hard_live=False),
        _objective(),
        [
            _action().model_copy(
                update={
                    "resource_cost": {"compute": 2.0},
                    "risk_charge": 0.2,
                }
            )
        ],
    )
    assert not report.plan.accepted
    assert report.plan.status == "diagnostic"
    candidate = report.plan.candidates[0]
    assert not candidate.finite_scope_usable
    assert "phase-control action blocked by hard-domain gate" in candidate.reasons
    assert "phase-control action exceeds budget for compute" in candidate.reasons


def test_phase_control_plan_records_objective_and_remaining_budget_debt() -> None:
    action_a = _action("a").model_copy(
        update={
            "activation_delta": 1.0,
            "burden_delta": 0.0,
            "resource_cost": {"compute": 0.6},
            "residual_charge": 0.0,
            "risk_charge": 0.0,
        }
    )
    action_b = _action("b").model_copy(
        update={
            "activation_delta": 1.0,
            "burden_delta": 0.0,
            "resource_cost": {"compute": 0.6},
            "residual_charge": 0.0,
            "risk_charge": 0.0,
        }
    )
    objective = _objective().model_copy(update={"horizon": -1, "residual_budget": 0.0})
    report = build_phase_control_plan(_state(), objective, [action_a, action_b])
    assert not report.plan.accepted
    assert "phase-control objective horizon is negative" in report.plan.reasons
    assert "phase-control plan residual charge exceeds objective budget" in report.plan.reasons
    assert "ecpt-plan:b:remaining-budget:compute" in report.plan.residual_ledger.coordinates


def test_ecpt_category_adapters_are_fail_closed() -> None:
    assert verify_ecpt_bridge_reserve(
        {"ecpt": "trc"},
        {"ecpt": "trc"},
        reserve=1.0,
        minimum_reserve=0.5,
    ).accepted
    assert not verify_ecpt_bridge_reserve(
        {},
        {"ecpt": "trc"},
        reserve=0.0,
        minimum_reserve=1.0,
    ).accepted
    assert not verify_ecpt_bridge_reserve(
        {},
        {},
        reserve=-1.0,
        minimum_reserve=0.0,
    ).accepted
    assert verify_ecpt_trace_diagnostic_projection({"t1"}, {"t1"}).accepted
    assert not verify_ecpt_trace_diagnostic_projection({"t1"}, set()).accepted
    assert not verify_ecpt_trace_diagnostic_projection(set(), set(), residual=-1.0).accepted
    assert verify_ecpt_domain_abstraction(
        {"model": "domain"},
        {"domain"},
        refinement_residual=0.1,
        residual_bound=0.2,
    ).accepted
    assert not verify_ecpt_domain_abstraction(
        {},
        {"domain"},
        refinement_residual=0.3,
        residual_bound=0.2,
    ).accepted
    assert not verify_ecpt_execution_policy(
        {"deploy"},
        set(),
        counterfactual_residual=0.1,
        residual_bound=0.2,
    ).accepted
    assert not verify_ecpt_execution_policy(
        set(),
        set(),
        counterfactual_residual=-1.0,
        residual_bound=0.0,
    ).accepted
    assert not verify_ecpt_execution_policy(
        {"deploy"},
        {"deploy"},
        counterfactual_residual=0.3,
        residual_bound=0.2,
    ).accepted
    assert verify_ecpt_proxy_target_contract(
        {"proxy": 0.8},
        {"proxy": 0.7},
        mismatch_residual=0.01,
        residual_bound=0.02,
    ).accepted
    assert not verify_ecpt_proxy_target_contract(
        {},
        {"proxy": 0.7},
        mismatch_residual=0.03,
        residual_bound=0.02,
    ).accepted
    assert not verify_ecpt_proxy_target_contract(
        {},
        {},
        mismatch_residual=-1.0,
        residual_bound=0.0,
    ).accepted
    assert not verify_ecpt_speculative_channel_repair(
        {"a"},
        set(),
        {"a", "b"},
        repair_residual=0.1,
        residual_bound=0.2,
    ).accepted
    assert not verify_ecpt_speculative_channel_repair(
        set(),
        set(),
        set(),
        repair_residual=-1.0,
        residual_bound=0.0,
    ).accepted
    assert not verify_ecpt_speculative_channel_repair(
        {"a"},
        set(),
        {"a"},
        repair_residual=0.3,
        residual_bound=0.2,
    ).accepted


def test_ecpt_planning_schemas_are_public() -> None:
    for name in [
        "ASIProxyTargetContract",
        "PhaseControlObjective",
        "PhaseControlState",
        "PhaseControlAction",
        "InterventionCandidate",
        "PhaseControlPlan",
        "PhaseControlRunReport",
    ]:
        schema = schema_by_type(name)
        assert schema["title"] == name


def test_cli_ecpt_plan_simulate_and_route_obligations(tmp_path: Path) -> None:
    plan = runner.invoke(
        app,
        [
            "ecpt",
            "plan",
            "--state",
            "examples/ecpt_phase_control_state.json",
            "--target",
            "examples/ecpt_asi_proxy_target.json",
            "--budget",
            "examples/ecpt_phase_control_budget.json",
            "--profile",
            "production",
        ],
    )
    assert plan.exit_code == 0, plan.output
    plan_data = json.loads(plan.output)
    assert plan_data["plan"]["selected_actions"]
    assert not plan_data["plan"]["settled"]
    assert "proxy-target-grounding-proof" in plan_data["plan"]["missing_obligations"]

    simulate = runner.invoke(
        app,
        [
            "ecpt",
            "simulate",
            "--state",
            "examples/ecpt_phase_control_state.json",
            "--actions",
            "examples/ecpt_phase_control_actions.json",
        ],
    )
    assert simulate.exit_code == 0, simulate.output
    simulate_data = json.loads(simulate.output)
    assert "phase-transition-proxy" in simulate_data["controlled_reachable_mass"]

    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "external_obligation_items": [
                    {
                        "item_id": "def:proxy",
                        "label": "proxy",
                        "obligation_category": "ecpt-proxy-target",
                        "verifier_route": "ecpt.adapters.proxy.verify_target_contract",
                        "safe_default": "diagnostic",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    routed = runner.invoke(app, ["ecpt", "route-obligations", "--audit", str(audit)])
    assert routed.exit_code == 0, routed.output
    routed_data = json.loads(routed.output)
    item = routed_data["routed_obligations"][0]
    assert item["route_known"]
    assert item["binding"]["implemented_route_id"] == (
        "adapters.domain.verify_ecpt_proxy_target_contract"
    )
