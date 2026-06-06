"""Optional local HTTP service for the ECPT active runtime."""

from __future__ import annotations

import importlib
import os
from typing import Any

from percolation_inversion_compiler.core import (
    VerifierEvidenceEnvelope,
    list_adapter_route_specs,
    resolve_adapter_route,
)
from percolation_inversion_compiler.ecology import ingest_agent_output, ingest_live_source
from percolation_inversion_compiler.ecology.connectors import infer_live_kind
from percolation_inversion_compiler.runtime.algorithms import (
    apply_action_results,
    build_runtime_step,
    certify_runtime_acceleration,
    compare_runtime_runs,
    resolve_step_evidence,
    run_runtime_loop,
)
from percolation_inversion_compiler.runtime.records import (
    AgentRuntimeConfig,
    RuntimeActionResult,
    RuntimeRunReport,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)


def create_runtime_app(settings: RuntimeServiceSettings | None = None) -> Any:
    """Create a FastAPI app if the optional server extra is installed."""

    active_settings = settings or RuntimeServiceSettings()
    try:
        fastapi = importlib.import_module("fastapi")
    except ModuleNotFoundError as exc:  # pragma: no cover - covered by CLI diagnostic path
        raise RuntimeError("runtime service requires the [server] extra") from exc

    fastapi_app = fastapi.FastAPI(
        title="Percolation Inversion Compiler Runtime",
        version="0.3.1",
        description="Local-first ECPT active ASI-proxy phase-control runtime service.",
    )
    http_exception = fastapi.HTTPException
    request_type = fastapi.Request

    def require_auth(authorization: str | None) -> None:
        required = (
            active_settings.profile == "production"
            if active_settings.require_token is None
            else active_settings.require_token
        )
        if not required:
            return
        token = os.environ.get(active_settings.token_env_var)
        if not token:
            raise http_exception(
                status_code=503,
                detail=_diagnostic("runtime token is not configured"),
            )
        if authorization != f"Bearer {token}":
            raise http_exception(status_code=401, detail=_diagnostic("invalid bearer token"))

    async def service_health(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        return {
            "accepted": True,
            "finite_checks_passed": True,
            "operationally_usable": active_settings.profile != "production"
            or bool(os.environ.get(active_settings.token_env_var)),
            "settled": False,
            "profile": active_settings.profile,
            "host": active_settings.host,
            "allow_live_connectors": active_settings.allow_live_connectors,
            "safety_invariants": [
                "service is local-first",
                "production profile requires bearer auth",
                "live connectors require explicit request opt-in",
            ],
        }

    async def runtime_step(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        state = RuntimeState.model_validate(payload.get("state"))
        step_input = RuntimeStepInput.model_validate(payload.get("input"))
        config = AgentRuntimeConfig.model_validate(payload.get("config", {}))
        config = _service_config(config, active_settings, step_input.allow_live_connectors)
        report = build_runtime_step(state, step_input, config)
        return report.model_dump(mode="json")

    async def runtime_loop(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        state = RuntimeState.model_validate(payload.get("state"))
        inputs = [RuntimeStepInput.model_validate(item) for item in payload.get("inputs", [])]
        config = AgentRuntimeConfig.model_validate(payload.get("config", {}))
        config = _service_config(config, active_settings, False)
        reports = run_runtime_loop(
            state,
            inputs,
            config,
            max_steps=int(payload.get("max_steps", len(inputs))),
        )
        return {"reports": [report.model_dump(mode="json") for report in reports]}

    async def runtime_result_apply(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        state = RuntimeState.model_validate(payload.get("state"))
        report = RuntimeStepReport.model_validate(payload.get("report"))
        results = [RuntimeActionResult.model_validate(item) for item in payload.get("results", [])]
        next_state = apply_action_results(state, report, results)
        return next_state.model_dump(mode="json")

    async def runtime_evidence_resolve(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        step_input = RuntimeStepInput.model_validate(payload.get("input", payload))
        profile = str(payload.get("profile", active_settings.profile))
        batch = resolve_step_evidence(step_input, profile=profile)
        return batch.model_dump(mode="json")

    async def runtime_compare(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        baseline = RuntimeRunReport.model_validate(payload.get("baseline"))
        candidate = RuntimeRunReport.model_validate(payload.get("candidate"))
        threshold = payload.get("threshold", {})
        comparison = compare_runtime_runs(baseline, candidate, threshold)
        return comparison.model_dump(mode="json")

    async def runtime_certify_acceleration(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        baseline = RuntimeRunReport.model_validate(payload.get("baseline"))
        candidate = RuntimeRunReport.model_validate(payload.get("candidate"))
        threshold = payload.get("threshold", {})
        certificate = certify_runtime_acceleration(baseline, candidate, threshold)
        return certificate.model_dump(mode="json")

    async def ecology_ingest(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        source = str(payload.get("source", ""))
        kind = str(payload.get("kind", "agent-output"))
        allow_live = bool(payload.get("allow_live_connectors", False))
        if kind == "agent-output":
            report = ingest_agent_output(source, output_id=str(payload.get("output_id", "service")))
        elif allow_live and active_settings.allow_live_connectors:
            report = ingest_live_source(source, kind=infer_live_kind(source))
        else:
            report = ingest_agent_output(
                f"diagnostic: live connector disabled for source kind {kind}",
                output_id="diagnostic-live-disabled",
            )
            report = report.model_copy(
                update={"accepted": False, "reasons": ["live connector disabled"]}
            )
        return report.model_dump(mode="json")

    async def evidence_verify(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        payload = await request.json()
        envelope_data = payload.get("envelope", payload)
        envelope = VerifierEvidenceEnvelope.model_validate(envelope_data)
        specs = {spec.route_id: spec for spec in list_adapter_route_specs()}
        spec = specs.get(envelope.route_id)
        if spec is None:
            raise http_exception(status_code=422, detail=_diagnostic("unknown adapter route"))
        profile = str(payload.get("profile", active_settings.profile))
        resolution = resolve_adapter_route(spec, envelope, profile=profile)
        return resolution.model_dump(mode="json")

    async def openapi_schema(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        schema: dict[str, Any] = fastapi_app.openapi()
        return schema

    for function in [
        service_health,
        runtime_step,
        runtime_loop,
        runtime_result_apply,
        runtime_evidence_resolve,
        runtime_compare,
        runtime_certify_acceleration,
        ecology_ingest,
        evidence_verify,
        openapi_schema,
    ]:
        function.__annotations__["request"] = request_type

    fastapi_app.add_api_route("/health", service_health, methods=["GET"])
    fastapi_app.add_api_route("/runtime/step", runtime_step, methods=["POST"])
    fastapi_app.add_api_route("/runtime/loop", runtime_loop, methods=["POST"])
    fastapi_app.add_api_route("/runtime/result/apply", runtime_result_apply, methods=["POST"])
    fastapi_app.add_api_route(
        "/runtime/evidence/resolve",
        runtime_evidence_resolve,
        methods=["POST"],
    )
    fastapi_app.add_api_route("/runtime/compare", runtime_compare, methods=["POST"])
    fastapi_app.add_api_route(
        "/runtime/certify-acceleration",
        runtime_certify_acceleration,
        methods=["POST"],
    )
    fastapi_app.add_api_route("/ecology/ingest", ecology_ingest, methods=["POST"])
    fastapi_app.add_api_route("/evidence/verify", evidence_verify, methods=["POST"])
    fastapi_app.add_api_route("/schemas/openapi.json", openapi_schema, methods=["GET"])
    return fastapi_app


def run_runtime_service(settings: RuntimeServiceSettings) -> None:
    """Run the optional Uvicorn service."""

    try:
        uvicorn = importlib.import_module("uvicorn")
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by CLI diagnostic path
        raise RuntimeError("runtime service requires the [server] extra") from exc
    uvicorn.run(create_runtime_app(settings), host=settings.host, port=settings.port)


def _service_config(
    config: AgentRuntimeConfig,
    settings: RuntimeServiceSettings,
    request_allows_live: bool,
) -> AgentRuntimeConfig:
    return config.model_copy(
        update={
            "profile": settings.profile,
            "allow_live_connectors": bool(
                settings.allow_live_connectors
                and config.allow_live_connectors
                and request_allows_live
            ),
        }
    )


def _authorization(request: Any) -> str | None:
    value = request.headers.get("authorization")
    return str(value) if value is not None else None


def _diagnostic(reason: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "finite_checks_passed": False,
        "operationally_usable": False,
        "settled": False,
        "reason": reason,
    }
