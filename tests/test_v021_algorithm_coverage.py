from __future__ import annotations

import pytest

from percolation_inversion_compiler.adapters.domain import (
    replay_trc_physical_trace,
    verify_archive_domain_evidence,
    verify_ecpt_generator_limit,
    verify_ecpt_numerical_envelope,
    verify_trc_telemetry_calibration,
)
from percolation_inversion_compiler.adapters.optimization import solve_linear_release
from percolation_inversion_compiler.core.certificates import (
    CertificateFamily,
    CertificateRoute,
    RefreshRule,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.order import FiniteOrder, LatticeWitness, ProductOrder
from percolation_inversion_compiler.core.status import ClaimStatus


def test_certificate_family_success_expiry_and_residuals() -> None:
    construction = CertificateRoute(route_id="construct", obligation_id="construct", accepted=True)
    verifier = CertificateRoute(route_id="verify", obligation_id="verify", accepted=True)
    settlement = CertificateRoute(
        route_id="settle",
        obligation_id="settle",
        accepted=False,
        cost=Ledger().add_coordinate("cost", 1.0, kind=CoordinateKind.BURDEN),
    )
    family = CertificateFamily(
        family_id="family",
        construction_routes=[construction],
        verifier_routes=[verifier],
        settlement_routes=[settlement],
        refresh_rule=RefreshRule(live_obligations={"domain"}),
    )
    result = family.check()
    assert result.status == ClaimStatus.PROVISIONAL
    assert "settle" in result.missing_obligations
    assert family.residual_ledger().value("settle:route-not-accepted") == 1.0

    expired = family.model_copy(
        update={"refresh_rule": RefreshRule(expired_obligations={"verify"})}
    ).check()
    assert not expired.accepted
    assert expired.status == ClaimStatus.EXPIRED
    assert "certificate family has expired obligations" in expired.reasons


def test_lattice_witness_and_product_order() -> None:
    order = FiniteOrder(
        elements=["bottom", "left", "right", "top"],
        leq_pairs=[
            ("bottom", "left"),
            ("bottom", "right"),
            ("left", "top"),
            ("right", "top"),
        ],
    )
    lattice = LatticeWitness(
        order=order,
        meet_table={
            "bottom|left": "bottom",
            "bottom|right": "bottom",
            "bottom|top": "bottom",
            "left|right": "bottom",
            "left|top": "left",
            "right|top": "right",
        },
        join_table={
            "bottom|left": "left",
            "bottom|right": "right",
            "bottom|top": "top",
            "left|right": "top",
            "left|top": "top",
            "right|top": "top",
        },
    )
    assert lattice.check().accepted
    broken = lattice.model_copy(update={"meet_table": {"left|right": "left"}})
    assert not broken.check().accepted

    product = ProductOrder(coordinate_orders={"x": order, "y": order})
    assert product.leq({"x": "bottom", "y": "left"}, {"x": "left", "y": "top"})
    assert not product.leq({"x": "top", "y": "left"}, {"x": "left", "y": "top"})


def test_domain_adapters_success_and_failure_cases() -> None:
    assert verify_ecpt_numerical_envelope(
        residual=0.1,
        residual_bound=0.2,
        finite_horizon=3,
    ).accepted
    failed_envelope = verify_ecpt_numerical_envelope(
        residual=0.3,
        residual_bound=0.2,
        finite_horizon=-1,
    )
    assert not failed_envelope.accepted
    assert failed_envelope.residual_ledger.value("ecpt:numerical-envelope:gap") > 0.0

    assert verify_ecpt_generator_limit(
        observed_generation=3.0,
        certified_limit=3.0,
    ).accepted
    assert not verify_ecpt_generator_limit(
        observed_generation=4.0,
        certified_limit=3.0,
        residual_allowance=0.1,
    ).accepted

    assert verify_trc_telemetry_calibration(
        [1.0, 2.0],
        [1.05, 2.05],
        tolerance=0.1,
    ).accepted
    assert not verify_trc_telemetry_calibration([1.0], [2.0], tolerance=0.1).accepted

    assert replay_trc_physical_trace(["a"], ["a", "b"], allow_prefix=True).accepted
    assert not replay_trc_physical_trace(["b"], ["a"], allow_prefix=False).accepted

    assert verify_archive_domain_evidence({"record": "thermal"}, {"thermal"}).accepted
    failed_archive = verify_archive_domain_evidence({"record": "power"}, {"thermal"})
    assert not failed_archive.accepted
    assert failed_archive.residual_ledger.value("trc:archive-domain:record") == 1.0


def test_linear_release_adapter_edges() -> None:
    assert solve_linear_release([1.0, -2.0], [0.0, 1.0], [3.0, 4.0]) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="equal length"):
        solve_linear_release([1.0], [], [])
    with pytest.raises(ValueError, match="lower bound exceeds"):
        solve_linear_release([1.0], [2.0], [1.0])
