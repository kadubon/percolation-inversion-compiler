"""Optional local HTTP service for the ECPT active runtime."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.core import (
    VerifierEvidenceEnvelope,
    list_adapter_route_specs,
    resolve_adapter_route,
)
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    GeneralIntakePolicy,
    GeneralIntakeSource,
    PacketSourceKind,
    ProtocolFrameDigest,
    WebFetchPolicy,
    check_no_hidden_capability_injection,
    find_autocatalytic_closures,
    find_execution_available_paths,
    infer_live_kind,
    ingest_agent_output,
    ingest_general_source,
    ingest_live_source,
    registry_from_json,
)
from percolation_inversion_compiler.runtime.algorithms import (
    apply_action_results,
    build_population_runtime_step,
    build_runtime_step,
    certify_collective_phase,
    certify_runtime_acceleration,
    compare_runtime_runs,
    execute_route_batch,
    execute_runtime_task,
    resolve_step_evidence,
    run_agent_loop_with_store,
    run_runtime_loop,
)
from percolation_inversion_compiler.runtime.records import (
    AgentPopulationState,
    AgentRuntimeConfig,
    AgentTask,
    RouteExecutionRequest,
    RuntimeActionResult,
    RuntimeExecutorPolicy,
    RuntimeRunReport,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)
from percolation_inversion_compiler.runtime.store import SQLiteRuntimeStore


def create_runtime_app(settings: RuntimeServiceSettings | None = None) -> Any:
    """Create a FastAPI app if the optional server extra is installed."""

    active_settings = settings or RuntimeServiceSettings()
    try:
        fastapi = importlib.import_module("fastapi")
    except ModuleNotFoundError as exc:  # pragma: no cover - covered by CLI diagnostic path
        raise RuntimeError("runtime service requires the [server] extra") from exc

    fastapi_app = fastapi.FastAPI(
        title="Percolation Inversion Compiler Runtime",
        version=__version__,
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
        _check_request_size(request, active_settings.max_request_bytes)
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
        _check_request_size(request, active_settings.max_request_bytes)
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
        _check_request_size(request, active_settings.max_request_bytes)
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
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        step_input = RuntimeStepInput.model_validate(payload.get("input", payload))
        profile = str(payload.get("profile", active_settings.profile))
        batch = resolve_step_evidence(step_input, profile=profile)
        return batch.model_dump(mode="json")

    async def runtime_compare(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
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
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        baseline = RuntimeRunReport.model_validate(payload.get("baseline"))
        candidate = RuntimeRunReport.model_validate(payload.get("candidate"))
        threshold = payload.get("threshold", {})
        certificate = certify_runtime_acceleration(baseline, candidate, threshold)
        return certificate.model_dump(mode="json")

    async def runtime_task_execute(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        state = RuntimeState.model_validate(payload.get("state"))
        task = AgentTask.model_validate(payload.get("task"))
        policy = RuntimeExecutorPolicy.model_validate(payload.get("policy", {}))
        policy = policy.model_copy(
            update={
                "profile": active_settings.profile,
                "allowed_route_ids": policy.allowed_route_ids or active_settings.allowed_route_ids,
            }
        )
        return execute_runtime_task(task, state, policy).model_dump(mode="json")

    async def runtime_routes_execute(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        requests = [
            RouteExecutionRequest.model_validate(item) for item in payload.get("requests", [])
        ]
        policy = RuntimeExecutorPolicy.model_validate(payload.get("policy", {}))
        policy = policy.model_copy(
            update={
                "profile": active_settings.profile,
                "allowed_route_ids": policy.allowed_route_ids or active_settings.allowed_route_ids,
            }
        )
        return execute_route_batch(
            requests,
            None,
            policy,
            profile=active_settings.profile,
        ).model_dump(mode="json")

    async def runtime_store_append(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        store = SQLiteRuntimeStore(Path(str(payload.get("store", "runtime-store.sqlite"))).name)
        if "state" in payload:
            store.append_state(RuntimeState.model_validate(payload["state"]))
        if "run" in payload:
            store.append_run(RuntimeRunReport.model_validate(payload["run"]))
        return store.record().model_dump(mode="json")

    async def runtime_store_load(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        store = SQLiteRuntimeStore(Path(str(payload.get("store", "runtime-store.sqlite"))).name)
        state = store.load_state(str(payload.get("state_id", "")))
        if state is None:
            return {"accepted": False, "settled": False, "reasons": ["runtime state not found"]}
        return state.model_dump(mode="json")

    async def runtime_run_agent_loop(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        state = RuntimeState.model_validate(payload.get("state"))
        inputs = [RuntimeStepInput.model_validate(item) for item in payload.get("inputs", [])]
        policy = RuntimeExecutorPolicy.model_validate(payload.get("policy", {}))
        policy = policy.model_copy(update={"profile": active_settings.profile})
        store_ref = payload.get("store")
        store = SQLiteRuntimeStore(Path(str(store_ref)).name) if store_ref else None
        reports = run_agent_loop_with_store(
            state,
            inputs,
            policy,
            store,
            max_steps=int(payload.get("max_steps", len(inputs))),
        )
        return {"reports": [report.model_dump(mode="json") for report in reports]}

    async def runtime_population_step(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        population = AgentPopulationState.model_validate(payload.get("population"))
        inputs = [RuntimeStepInput.model_validate(item) for item in payload.get("inputs", [])]
        config = AgentRuntimeConfig.model_validate(payload.get("config", {}))
        config = _service_config(config, active_settings, False)
        report = build_population_runtime_step(population, inputs, config)
        return report.model_dump(mode="json")

    async def runtime_collective_certify(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        certificate = certify_collective_phase(
            AgentPopulationState.model_validate(payload.get("population")),
            RuntimeState.model_validate(payload.get("state")),
            CapabilityBasinContract.model_validate(payload.get("basin")),
            RuntimeRunReport.model_validate(payload.get("baseline")),
            payload.get("threshold", {}),
            profile=active_settings.profile,
        )
        return certificate.model_dump(mode="json")

    async def ecology_closures(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        registry = registry_from_json(payload.get("registry", payload))
        basin_payload = payload.get("basin")
        basin = (
            None if basin_payload is None else CapabilityBasinContract.model_validate(basin_payload)
        )
        closures = find_autocatalytic_closures(registry, basin)
        return {"closures": [closure.model_dump(mode="json") for closure in closures]}

    async def ecology_execution_paths(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        registry = registry_from_json(payload.get("registry", payload))
        basin = CapabilityBasinContract.model_validate(payload.get("basin"))
        paths = find_execution_available_paths(
            registry,
            basin,
            constraint_frame=payload.get("constraint_frame"),
        )
        return {"execution_available_paths": [path.model_dump(mode="json") for path in paths]}

    async def ecology_hidden_injection_check(request: Any) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        registry = registry_from_json(payload.get("registry", payload))
        protocol = ProtocolFrameDigest.model_validate(payload.get("protocol"))
        events = payload.get("events", [])
        report = check_no_hidden_capability_injection(
            registry,
            protocol,
            runtime_events=[item for item in events if isinstance(item, dict)],
        )
        return report.model_dump(mode="json")

    async def ecology_ingest(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
        payload = await request.json()
        source = str(payload.get("source", ""))
        kind = str(payload.get("kind", "agent-output"))
        allow_live = bool(
            payload.get("allow_live_connectors", active_settings.allow_live_connectors)
        )
        if kind == "agent-output":
            report = ingest_agent_output(source, output_id=str(payload.get("output_id", "service")))
        elif (
            allow_live
            and active_settings.allow_live_connectors
            and kind
            in {
                "github",
                "zenodo",
                "arxiv",
            }
        ):
            report = ingest_live_source(source, kind=infer_live_kind(source))
        else:
            general_report = ingest_general_source(
                GeneralIntakeSource(
                    source=source,
                    kind=PacketSourceKind(kind)
                    if kind in {item.value for item in PacketSourceKind}
                    else PacketSourceKind.AUTO,
                    allow_live_connectors=allow_live,
                ),
                GeneralIntakePolicy(
                    profile=active_settings.profile,
                    allow_live_connectors=allow_live and active_settings.allow_live_connectors,
                    web_policy=WebFetchPolicy(
                        allow_live_connectors=allow_live and active_settings.allow_live_connectors
                    ),
                ),
            )
            return general_report.model_dump(mode="json")
        if kind != "agent-output" and allow_live and not active_settings.allow_live_connectors:
            report = report.model_copy(
                update={
                    "accepted": False,
                    "reasons": ["service live connector disabled"],
                }
            )
        return report.model_dump(mode="json")

    async def evidence_verify(
        request: Any,
    ) -> dict[str, Any]:
        require_auth(_authorization(request))
        _check_request_size(request, active_settings.max_request_bytes)
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
        runtime_task_execute,
        runtime_routes_execute,
        runtime_store_append,
        runtime_store_load,
        runtime_run_agent_loop,
        runtime_population_step,
        runtime_collective_certify,
        ecology_closures,
        ecology_execution_paths,
        ecology_hidden_injection_check,
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
    fastapi_app.add_api_route("/runtime/task/execute", runtime_task_execute, methods=["POST"])
    fastapi_app.add_api_route("/runtime/routes/execute", runtime_routes_execute, methods=["POST"])
    fastapi_app.add_api_route("/runtime/store/append", runtime_store_append, methods=["POST"])
    fastapi_app.add_api_route("/runtime/store/load", runtime_store_load, methods=["POST"])
    fastapi_app.add_api_route("/runtime/run-agent-loop", runtime_run_agent_loop, methods=["POST"])
    fastapi_app.add_api_route("/runtime/population/step", runtime_population_step, methods=["POST"])
    fastapi_app.add_api_route(
        "/runtime/collective/certify",
        runtime_collective_certify,
        methods=["POST"],
    )
    fastapi_app.add_api_route("/ecology/closures", ecology_closures, methods=["POST"])
    fastapi_app.add_api_route("/ecology/execution-paths", ecology_execution_paths, methods=["POST"])
    fastapi_app.add_api_route(
        "/ecology/hidden-injection-check",
        ecology_hidden_injection_check,
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


def _check_request_size(request: Any, limit: int) -> None:
    raw = request.headers.get("content-length")
    if raw is None:
        return
    try:
        size = int(raw)
    except ValueError:
        return
    if size > limit:
        raise RuntimeError("runtime request exceeds configured size limit")


def _diagnostic(reason: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "finite_checks_passed": False,
        "operationally_usable": False,
        "settled": False,
        "reason": reason,
    }
