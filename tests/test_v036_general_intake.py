from __future__ import annotations

import json
from types import SimpleNamespace

from percolation_inversion_compiler.ecology import (
    AgentInboxRecord,
    AgentMessageEnvelope,
    AgentMessageVerificationContext,
    AutocatalyticClosureWitness,
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    EdgeWitness,
    ExecutionAvailablePathCertificate,
    GeneralIntakePolicy,
    GeneralIntakeSource,
    PacketSourceKind,
    WebFetchPolicy,
    append_agent_message,
    audit_general_intake_report,
    bridge_general_intake_to_runtime,
    build_packet_registry,
    build_psi_dashboard,
    check_agent_message_contract,
    classify_external_candidate_for_sqot,
    create_agent_message,
    discover_web_packets,
    fetch_http_resource,
    general_intake_policy_for_profile,
    general_intake_to_packet_ingestion,
    ingest_agent_inbox,
    ingest_feed,
    ingest_general_source,
    read_agent_inbox,
    sanitize_intake_source_ref,
    verify_agent_message,
)
from percolation_inversion_compiler.ecology.algorithms import sha256_text


def test_fetch_http_requires_opt_in_and_rejects_private_hosts() -> None:
    disabled = fetch_http_resource("https://example.org")
    assert not disabled.accepted
    assert "allow_live_connectors=true" in disabled.reasons[0]
    assert disabled.web_fetch_reports[0].requested_url == "https://example.org/"
    assert any(":diagnostic:" in key for key in disabled.residual_ledger.coordinates)
    assert disabled.provenance[0].residual_coordinates == sorted(
        disabled.residual_ledger.coordinates
    )

    private = fetch_http_resource(
        "https://127.0.0.1/resource",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert not private.accepted
    assert "private" in private.reasons[0]
    assert private.web_fetch_reports[0].final_url == "https://127.0.0.1/resource"
    assert any(":diagnostic:" in key for key in private.residual_ledger.coordinates)


def test_fetch_http_with_fake_httpx_success_and_content_type_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=b"<html><title>ECPT live fixture</title><body>packet</body></html>",
                encoding="utf-8",
                url="https://example.org/packet?token=redacted",
                history=[],
            )

    import percolation_inversion_compiler.ecology.general_intake as general_intake

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: FakeHttpx)
    report = fetch_http_resource(
        "https://example.org/packet",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert report.accepted
    assert report.source_kind == PacketSourceKind.WEB_PAGE
    assert report.provenance[0].content_sha256
    assert "?" not in report.provenance[0].public_source_ref
    assert report.web_fetch_reports[0].final_url == "https://example.org/packet"
    assert report.web_fetch_reports[0].content_sha256

    class BadTypeHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "application/octet-stream"},
                content=b"binary",
                encoding="utf-8",
                url="https://example.org/binary",
                history=[],
            )

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: BadTypeHttpx)
    rejected = fetch_http_resource(
        "https://example.org/binary",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert not rejected.accepted
    assert "unsupported content type" in rejected.reasons[0]
    assert rejected.web_fetch_reports[0].content_type == "application/octet-stream"
    assert rejected.provenance[0].residual_coordinates == sorted(
        rejected.residual_ledger.coordinates
    )


def test_fetch_http_rejects_unsafe_redirect_chain(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class RedirectHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/plain"},
                content=b"redirected packet",
                encoding="utf-8",
                url="https://example.org/final",
                history=[SimpleNamespace(url="https://127.0.0.1/internal")],
            )

    import percolation_inversion_compiler.ecology.general_intake as general_intake

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: RedirectHttpx)
    rejected = fetch_http_resource(
        "https://example.org/packet",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert not rejected.accepted
    assert "redirect chain URL rejected" in "; ".join(rejected.reasons)
    assert rejected.web_fetch_reports[0].redirect_chain == [
        "https://127.0.0.1/internal",
        "https://example.org/final",
    ]
    assert rejected.provenance[0].residual_coordinates == sorted(
        rejected.residual_ledger.coordinates
    )


def test_fetch_http_failure_branches_are_diagnostic(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import percolation_inversion_compiler.ecology.general_intake as general_intake

    monkeypatch.setattr(
        general_intake.importlib,
        "import_module",
        lambda _: (_ for _ in ()).throw(ModuleNotFoundError("httpx")),
    )
    missing_dependency = fetch_http_resource(
        "https://example.org/packet",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert not missing_dependency.accepted
    assert "httpx" in missing_dependency.reasons[0]
    assert missing_dependency.web_fetch_reports[0].reasons == [
        "optional connector dependency 'httpx' is not installed"
    ]

    class ErrorHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            raise RuntimeError("transport down")

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: ErrorHttpx)
    failed_request = fetch_http_resource(
        "https://example.org/packet",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert not failed_request.accepted
    assert "connector request failed" in failed_request.reasons[0]

    class StatusHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            return SimpleNamespace(
                status_code=503,
                headers={"content-type": "text/plain"},
                content=b"unavailable",
                encoding="utf-8",
                url="https://example.org/packet",
                history=[],
            )

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: StatusHttpx)
    bad_status = fetch_http_resource(
        "https://example.org/packet",
        WebFetchPolicy(allow_live_connectors=True),
    )
    assert not bad_status.accepted
    assert "http status 503" in bad_status.reasons[0]
    assert bad_status.web_fetch_reports[0].status_code == 503
    assert bad_status.provenance[0].residual_coordinates == sorted(
        bad_status.residual_ledger.coordinates
    )

    class OversizedHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/plain"},
                content=b"abcdef",
                encoding="utf-8",
                url="https://example.org/packet",
                history=[],
            )

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: OversizedHttpx)
    oversized = fetch_http_resource(
        "https://example.org/packet",
        WebFetchPolicy(allow_live_connectors=True, max_bytes_per_resource=3),
    )
    assert not oversized.accepted
    assert "exceeds" in oversized.reasons[0]
    assert oversized.provenance[0].residual_coordinates == sorted(
        oversized.residual_ledger.coordinates
    )


def test_fetch_url_validation_failures_are_diagnostic() -> None:
    policy = WebFetchPolicy(allow_live_connectors=True)
    unsupported_scheme = fetch_http_resource(
        "ftp://user:secret@example.org/resource?token=redacted", policy
    )
    assert not unsupported_scheme.accepted
    assert "unsupported URL scheme" in unsupported_scheme.reasons[0]
    assert unsupported_scheme.web_fetch_reports[0].requested_url == ("ftp://example.org/resource")
    assert "secret" not in unsupported_scheme.provenance[0].public_source_ref
    assert "token" not in unsupported_scheme.provenance[0].public_source_ref

    http_without_allow = fetch_http_resource(
        "http://example.org/resource",
        policy.model_copy(update={"allowed_schemes": ["http", "https"]}),
    )
    assert not http_without_allow.accepted
    assert "requires HTTPS" in http_without_allow.reasons[0]

    missing_host = fetch_http_resource("https:///resource", policy)
    assert not missing_host.accepted
    assert "host is required" in missing_host.reasons[0]

    private_ip = fetch_http_resource("https://192.168.0.10/resource", policy)
    assert not private_ip.accepted
    assert "private" in private_ip.reasons[0]

    robots_uncertain = fetch_http_resource(
        "https://example.org/robots",
        WebFetchPolicy(allow_live_connectors=True, robots_uncertainty_is_diagnostic=True),
    )
    assert not robots_uncertain.accepted
    assert robots_uncertain.web_fetch_reports[0].robots_decision.mode == "uncertain"


def test_general_intake_policy_presets_and_url_scope() -> None:
    local_only = general_intake_policy_for_profile("local_only")
    assert not local_only.allow_live_connectors
    assert PacketSourceKind.GITHUB not in set(local_only.allowed_source_kinds)

    production = general_intake_policy_for_profile("production_network")
    assert production.require_signed_agent_messages
    assert production.require_message_identity_context
    assert production.web_policy.require_https_for_live
    assert production.web_policy.require_robots_decision

    scoped = fetch_http_resource(
        "https://blocked.example/packet",
        WebFetchPolicy(
            allow_live_connectors=True,
            allowed_hosts=["allowed.example"],
        ),
    )
    assert not scoped.accepted
    assert "outside allowed_hosts" in scoped.reasons[0]

    blocked = fetch_http_resource(
        "https://blocked.example/packet",
        WebFetchPolicy(
            allow_live_connectors=True,
            blocked_hosts=["blocked.example"],
        ),
    )
    assert not blocked.accepted
    assert "blocked_hosts" in blocked.reasons[0]

    path_rejected = fetch_http_resource(
        "https://allowed.example/private/packet",
        WebFetchPolicy(
            allow_live_connectors=True,
            allowed_hosts=["allowed.example"],
            allowed_path_prefixes=["/public"],
        ),
    )
    assert not path_rejected.accepted
    assert "allowed_path_prefixes" in path_rejected.reasons[0]


def test_general_intake_metadata_and_runtime_bridge(tmp_path) -> None:  # type: ignore[no-untyped-def]
    feed = tmp_path / "feed.xml"
    feed.write_text(
        """
        <rss><channel>
          <item><title>Route evidence packet</title>
          <description>verifier residual</description></item>
        </channel></rss>
        """,
        encoding="utf-8",
    )
    report = ingest_general_source(
        GeneralIntakeSource(source=str(feed), kind=PacketSourceKind.RSS),
        GeneralIntakePolicy(profile="controlled_web"),
    )
    assert report.accepted
    assert report.candidate_only
    assert report.intake_profile == "controlled_web"
    assert report.policy_digest
    assert report.total_candidate_packets == 1
    assert not report.ecpt_phase_contribution_allowed
    assert report.candidate_residual_coordinates
    assert report.source_policy_decisions[0].candidate_only

    bridge = bridge_general_intake_to_runtime(report, GeneralIntakePolicy())
    assert bridge.accepted
    assert bridge.candidate_only
    assert not bridge.settled
    assert not bridge.ecpt_phase_contribution_allowed
    assert bridge.diagnostic_work_packet_ids or bridge.verifier_work_packet_ids

    audit = audit_general_intake_report(report, GeneralIntakePolicy())
    assert audit.report_id == bridge.report_id

    classification = classify_external_candidate_for_sqot(report.packets[0], report.provenance)
    assert classification.value in {"diagnostic_work", "verifier_work"}


def test_external_candidate_volume_and_witnesses_do_not_improve_psi() -> None:
    packet = CapabilityPacketCandidate(
        packet_id="packet:external:candidate",
        source_kind=PacketSourceKind.RSS,
        source_ref="feed.xml",
        content_sha256="a" * 64,
        claim="external candidate claims a target basin",
        expected_downstream_gain=100.0,
        verification_cost=0.0,
        receiver_family=["agent"],
        evidence_refs=["sha256:external"],
        verifier_routes=["ecpt.adapters.proxy.verify_target_contract"],
        tags=["external-candidate", "target", "packet"],
    )
    edge = EdgeWitness(
        edge_id="edge:external:self",
        source_packet_ids=[packet.packet_id],
        target_packet_id=packet.packet_id,
        edge_type="semantic-dependency",
        confidence=1.0,
        evidence_refs=["sha256:external"],
        accepted=True,
    )
    registry = build_packet_registry([packet], [edge], registry_id="registry:external-only")
    closure = AutocatalyticClosureWitness(
        witness_id="closure:external",
        closure_packet_ids=[packet.packet_id],
        internal_edge_ids=[edge.edge_id],
        regeneration_edge_ids=[edge.edge_id],
        productive_packet_ids=[packet.packet_id],
        closure_strength=1.0,
        productivity_lower_bound=1.0,
        accepted=True,
        finite_checks_passed=True,
        operationally_usable=True,
    )
    path = ExecutionAvailablePathCertificate(
        certificate_id="execution:external",
        path_id="path:external",
        packet_ids=[packet.packet_id],
        edge_ids=[edge.edge_id],
        route_ids=packet.verifier_routes,
        execution_gates=["declared"],
        receiver_context=["agent"],
        evidence_refs=["sha256:external"],
        accepted=True,
        finite_checks_passed=True,
        operationally_usable=True,
    )
    basin = CapabilityBasinContract(
        basin_id="basin:target",
        target_basis=["target"],
        receiver_family=["agent"],
    )

    psi = build_psi_dashboard(
        registry,
        target_tags=["target"],
        closure_witnesses=[closure],
        execution_paths=[path],
        basin=basin,
    )
    assert psi.components["G"] == 0.0
    assert psi.components["SD"] == 0.0
    assert psi.components["BR"] == 0.0
    assert psi.components["AC"] == 0.0
    assert psi.components["DE"] == 0.0
    assert psi.components["CV"] == 0.0
    residual_names = set(psi.residual_ledger.coordinates)
    assert any("external-candidate-volume-excluded" in name for name in residual_names)
    assert any("external-candidate-closure-witness-excluded" in name for name in residual_names)
    assert any("external-candidate-execution-path-excluded" in name for name in residual_names)
    assert any("external-candidate-basin-path-excluded" in name for name in residual_names)


def test_total_packet_budget_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    feed = tmp_path / "feed.xml"
    feed.write_text(
        """
        <rss><channel>
          <item><title>A</title></item>
          <item><title>B</title></item>
        </channel></rss>
        """,
        encoding="utf-8",
    )
    report = ingest_general_source(
        GeneralIntakeSource(source=str(feed), kind=PacketSourceKind.RSS),
        GeneralIntakePolicy(web_policy=WebFetchPolicy(max_total_packets_per_run=1)),
    )
    assert not report.accepted
    assert "candidate packet count exceeds max_total_packets_per_run" in report.reasons
    assert any("packet-budget" in key for key in report.residual_ledger.coordinates)

    explicit_http_kind = ingest_general_source(
        GeneralIntakeSource(
            source="ftp://user:secret@example.org/resource?token=redacted",
            kind=PacketSourceKind.HTTP,
            allow_live_connectors=True,
        ),
        GeneralIntakePolicy(allow_live_connectors=True),
    )
    assert not explicit_http_kind.accepted
    assert explicit_http_kind.web_fetch_reports[0].requested_url == "ftp://example.org/resource"
    assert "secret" not in explicit_http_kind.source
    assert explicit_http_kind.provenance[0].residual_coordinates == sorted(
        explicit_http_kind.residual_ledger.coordinates
    )


def test_diagnostic_feed_and_inbox_preserve_active_policy_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    policy = general_intake_policy_for_profile("adversarial_network").model_copy(
        update={"allow_live_connectors": False}
    )

    malformed_feed = tmp_path / "broken.xml"
    malformed_feed.write_text("<rss><channel><item>", encoding="utf-8")
    feed_report = ingest_feed(str(malformed_feed), policy, kind=PacketSourceKind.RSS)
    assert not feed_report.accepted
    assert feed_report.candidate_only
    assert feed_report.intake_profile == "adversarial_network"
    assert feed_report.policy_digest
    assert not feed_report.ecpt_phase_contribution_allowed
    assert feed_report.source_policy_decisions[0].profile == "adversarial_network"

    malformed_inbox = tmp_path / "inbox.json"
    malformed_inbox.write_text("{not-json", encoding="utf-8")
    inbox_report = ingest_agent_inbox(str(malformed_inbox), policy)
    assert not inbox_report.accepted
    assert inbox_report.candidate_only
    assert inbox_report.intake_profile == "adversarial_network"
    assert inbox_report.policy_digest == feed_report.policy_digest
    assert inbox_report.source_policy_decisions[0].profile == "adversarial_network"


def test_general_auto_kind_web_crawl_and_live_connector_diagnostics(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import percolation_inversion_compiler.ecology.general_intake as general_intake

    class FakeHttpx:
        HTTPError = RuntimeError

        @staticmethod
        def get(*args, **kwargs) -> object:
            _ = args, kwargs
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"<html><title>Auto web packet</title></html>",
                encoding="utf-8",
                url="https://example.org/auto",
                history=[],
            )

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: FakeHttpx)
    auto_web = ingest_general_source(
        GeneralIntakeSource(source="https://example.org/auto", allow_live_connectors=True),
        GeneralIntakePolicy(allow_live_connectors=True),
    )
    assert auto_web.accepted
    assert auto_web.source_kind == PacketSourceKind.WEB_PAGE
    assert auto_web.provenance

    missing_source_opt_in = ingest_general_source(
        "https://example.org/auto",
        GeneralIntakePolicy(allow_live_connectors=True),
    )
    assert not missing_source_opt_in.accepted
    assert "source/request" in missing_source_opt_in.reasons[0]

    github_disabled = ingest_general_source("owner/repo")
    assert not github_disabled.accepted
    assert github_disabled.source_kind == PacketSourceKind.GITHUB
    assert "allow_live_connectors=true" in github_disabled.reasons[0]

    invalid_json = tmp_path / "broken.json"
    invalid_json.write_text("{not-json", encoding="utf-8")
    invalid_json_report = ingest_general_source(str(invalid_json))
    assert not invalid_json_report.accepted
    assert invalid_json_report.source_kind == PacketSourceKind.JSON_FEED

    unknown_local = tmp_path / "notes.txt"
    unknown_local.write_text("plain packet note", encoding="utf-8")
    local_report = ingest_general_source(str(unknown_local))
    assert not local_report.accepted
    assert "unsupported source kind local" in local_report.reasons[0]

    root = tmp_path / "root.html"
    linked = tmp_path / "linked.html"
    linked.write_text("<html><title>Linked candidate</title></html>", encoding="utf-8")
    root.write_text(
        "".join(
            [
                "<html><title>Root candidate</title>",
                '<a href="linked.html">one</a>',
                '<a href="linked.html">duplicate</a>',
                '<a href="#fragment">fragment</a>',
                '<a href="mailto:test@example.org">mail</a>',
                '<a href="javascript:void(0)">script</a>',
                '<a href="https://example.org/external">external</a>',
                "</html>",
            ]
        ),
        encoding="utf-8",
    )
    crawl = ingest_general_source(
        GeneralIntakeSource(source=str(root), kind=PacketSourceKind.WEB_CRAWL)
    )
    assert crawl.accepted
    assert crawl.source_kind == PacketSourceKind.WEB_CRAWL
    assert linked.name in crawl.discovered_links
    assert "https://example.org/external" in crawl.discovered_links
    assert all(str(tmp_path) not in item for item in crawl.discovered_links)


def test_feed_json_ndjson_and_discovery_offline(tmp_path) -> None:  # type: ignore[no-untyped-def]
    json_feed = tmp_path / "feed.json"
    json_feed.write_text(
        json.dumps({"items": [{"title": "ECPT JSON item", "summary": "candidate"}]}),
        encoding="utf-8",
    )
    json_report = ingest_feed(str(json_feed), kind=PacketSourceKind.JSON_FEED)
    assert json_report.accepted
    assert json_report.packets[0].source_kind == PacketSourceKind.JSON_FEED
    assert "external-candidate" in json_report.packets[0].tags

    ndjson = tmp_path / "items.ndjson"
    ndjson.write_text('{"claim":"packet one"}\n{"claim":"packet two"}\n', encoding="utf-8")
    ndjson_report = ingest_general_source(
        GeneralIntakeSource(source=str(ndjson), kind=PacketSourceKind.NDJSON)
    )
    assert ndjson_report.accepted
    assert len(ndjson_report.packets) == 2

    html = tmp_path / "page.html"
    linked = tmp_path / "linked.html"
    linked.write_text("<html><title>Linked ECPT packet</title></html>", encoding="utf-8")
    html.write_text(
        '<html><title>Root ECPT packet</title><a href="linked.html">next</a></html>',
        encoding="utf-8",
    )
    discovery = discover_web_packets(str(html))
    assert discovery.accepted
    assert len(discovery.packets) == 2
    assert linked.name in discovery.discovered_links

    oversized_local = tmp_path / "oversized.html"
    oversized_local.write_text("<html>too large</html>", encoding="utf-8")
    oversized_report = ingest_general_source(
        GeneralIntakeSource(source=str(oversized_local), kind=PacketSourceKind.WEB_PAGE),
        GeneralIntakePolicy(web_policy=WebFetchPolicy(max_bytes_per_resource=4)),
    )
    assert not oversized_report.accepted
    assert "exceeds max_bytes_per_resource" in oversized_report.reasons[0]


def test_live_discovery_fetches_each_page_once(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import percolation_inversion_compiler.ecology.general_intake as general_intake

    class CountingHttpx:
        HTTPError = RuntimeError
        calls = 0

        @classmethod
        def get(cls, *args, **kwargs) -> object:
            _ = args, kwargs
            cls.calls += 1
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/html"},
                content=(
                    b"<html><title>Live root</title>"
                    b'<a href="https://example.org/linked">linked</a></html>'
                ),
                encoding="utf-8",
                url="https://example.org/root",
                history=[],
            )

    monkeypatch.setattr(general_intake.importlib, "import_module", lambda _: CountingHttpx)
    discovery = discover_web_packets(
        "https://example.org/root",
        WebFetchPolicy(allow_live_connectors=True, max_depth=0),
    )
    assert discovery.accepted
    assert CountingHttpx.calls == 1
    assert "https://example.org/linked" in discovery.discovered_links


def test_local_discovery_does_not_follow_paths_outside_seed_directory(tmp_path) -> None:  # type: ignore[no-untyped-def]
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    root = root_dir / "page.html"
    inside = root_dir / "inside.html"
    outside = tmp_path / "outside.html"
    inside.write_text("<html><title>Inside packet</title></html>", encoding="utf-8")
    outside.write_text("<html><title>Outside packet</title></html>", encoding="utf-8")
    root.write_text(
        '<html><title>Root packet</title><a href="inside.html">inside</a>'
        '<a href="../outside.html">outside</a></html>',
        encoding="utf-8",
    )
    discovery = discover_web_packets(str(root))
    assert discovery.accepted
    assert inside.name in discovery.discovered_links
    assert outside.name not in discovery.discovered_links
    assert all("Outside packet" not in packet.claim for packet in discovery.packets)


def test_feed_malformed_and_unsupported_inputs_return_residuals(tmp_path) -> None:  # type: ignore[no-untyped-def]
    live_disabled = ingest_feed(
        "https://example.org/feed.xml",
        GeneralIntakePolicy(web_policy=WebFetchPolicy()),
        kind=PacketSourceKind.RSS,
    )
    assert not live_disabled.accepted
    assert "allow_live_connectors=true" in live_disabled.reasons[0]

    malformed_rss = tmp_path / "malformed.rss"
    malformed_rss.write_text("<rss><channel><item>", encoding="utf-8")
    malformed_report = ingest_feed(str(malformed_rss), kind=PacketSourceKind.RSS)
    assert not malformed_report.accepted
    assert malformed_report.residual_ledger.coordinates

    entity_rss = tmp_path / "entity.rss"
    entity_rss.write_text(
        '<!DOCTYPE rss [<!ENTITY x "boom">]><rss><channel><item><title>&x;</title></item>'
        "</channel></rss>",
        encoding="utf-8",
    )
    entity_report = ingest_feed(str(entity_rss), kind=PacketSourceKind.RSS)
    assert not entity_report.accepted
    assert entity_report.residual_ledger.coordinates

    empty_rss = tmp_path / "empty.rss"
    empty_rss.write_text("<rss><channel><item /></channel></rss>", encoding="utf-8")
    empty_report = ingest_feed(str(empty_rss), kind=PacketSourceKind.RSS)
    assert not empty_report.accepted

    json_nonlist = tmp_path / "nonlist.json"
    json_nonlist.write_text(json.dumps({"items": {"title": "not a list"}}), encoding="utf-8")
    nonlist_report = ingest_feed(str(json_nonlist), kind=PacketSourceKind.JSON_FEED)
    assert not nonlist_report.accepted

    json_list = tmp_path / "list.json"
    json_list.write_text(json.dumps(["string packet"]), encoding="utf-8")
    list_report = ingest_feed(str(json_list), kind=PacketSourceKind.JSON_FEED)
    assert list_report.accepted

    too_many_json = tmp_path / "too-many.json"
    too_many_json.write_text(json.dumps(["one", "two", "three"]), encoding="utf-8")
    too_many_report = ingest_feed(
        str(too_many_json),
        GeneralIntakePolicy(max_feed_entries=2),
        kind=PacketSourceKind.JSON_FEED,
    )
    assert not too_many_report.accepted
    assert "max_feed_entries" in "; ".join(too_many_report.reasons)

    bad_ndjson = tmp_path / "bad.ndjson"
    bad_ndjson.write_text('\n{"ok": true}\n{bad}\n', encoding="utf-8")
    ndjson_report = ingest_feed(str(bad_ndjson), kind=PacketSourceKind.NDJSON)
    assert not ndjson_report.accepted

    unsupported = ingest_feed(str(json_list), kind=PacketSourceKind.WEB_PAGE)
    assert not unsupported.accepted
    assert "unsupported feed kind" in unsupported.reasons[0]


def test_general_intake_policy_rejection_and_bad_message() -> None:
    rejected_kind = ingest_general_source(
        GeneralIntakeSource(source="literal", kind=PacketSourceKind.AGENT_OUTPUT),
        GeneralIntakePolicy(allowed_source_kinds=[PacketSourceKind.RSS]),
    )
    assert not rejected_kind.accepted
    assert "not allowed" in rejected_kind.reasons[0]

    bad_message = ingest_general_source(
        GeneralIntakeSource(source="{not-json", kind=PacketSourceKind.AGENT_MESSAGE)
    )
    assert not bad_message.accepted
    assert "invalid agent message JSON" in bad_message.reasons[0]

    huge_inline_message = ingest_general_source(
        GeneralIntakeSource(
            source='{"message_id":"m","sender_agent_id":"a","content":"xxxx"}',
            kind=PacketSourceKind.AGENT_MESSAGE,
        ),
        GeneralIntakePolicy(web_policy=WebFetchPolicy(max_bytes_per_resource=8)),
    )
    assert not huge_inline_message.accepted
    assert "max_bytes_per_resource" in huge_inline_message.reasons[0]

    invalid_path = ingest_general_source("bad\0path")
    assert not invalid_path.accepted
    assert invalid_path.source_kind == PacketSourceKind.LOCAL


def test_inline_agent_message_and_invalid_inbox_sources() -> None:
    message = create_agent_message("inline packet", sender_agent_id="agent:inline")
    inline_report = ingest_general_source(
        GeneralIntakeSource(
            source=message.model_dump_json(),
            kind=PacketSourceKind.AGENT_MESSAGE,
        )
    )
    assert inline_report.accepted
    assert inline_report.packets[0].issuer_agent_id == "agent:inline"

    bad_inbox = ingest_agent_inbox("{not-json")
    assert not bad_inbox.accepted
    assert "invalid agent inbox JSON" in bad_inbox.reasons[0]

    too_many_messages = json.dumps(
        [
            create_agent_message("one", sender_agent_id="agent:one").model_dump(mode="json"),
            create_agent_message("two", sender_agent_id="agent:two").model_dump(mode="json"),
        ]
    )
    too_many_inbox = ingest_agent_inbox(
        too_many_messages,
        GeneralIntakePolicy(max_agent_messages_per_inbox=1),
    )
    assert not too_many_inbox.accepted
    assert "max_agent_messages_per_inbox" in too_many_inbox.reasons[0]


def test_general_report_conversion_and_source_sanitization(tmp_path) -> None:  # type: ignore[no-untyped-def]
    message = create_agent_message("inline packet", sender_agent_id="agent:inline")
    inbox = tmp_path / "inbox.json"
    inbox.write_text(
        json.dumps({"messages": [message.model_dump(mode="json")]}),
        encoding="utf-8",
    )
    general = ingest_general_source(
        GeneralIntakeSource(source=str(inbox), kind=PacketSourceKind.AGENT_INBOX)
    )
    converted = general_intake_to_packet_ingestion(general)
    assert converted.source_kind == PacketSourceKind.AGENT_INBOX
    assert converted.packets
    assert sanitize_intake_source_ref("https://userinfo@example.org:443/x?q=redacted") == (
        "https://example.org:443/x"
    )
    assert sanitize_intake_source_ref('{"value":"not-output"}').startswith("inline-json:")
    assert sanitize_intake_source_ref("long\nliteral").startswith("literal:")


def test_agent_message_digest_signature_and_inbox_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    content = "Peer packet: preserve residuals."
    message = create_agent_message(
        content,
        sender_agent_id="agent:alice",
        receiver_agent_id="agent:bob",
        nonce="nonce-1",
    )
    assert message.content_sha256 == sha256_text(content)
    contract = check_agent_message_contract(message)
    assert contract.accepted
    assert contract.message_contract_valid
    assert contract.declared_packet_kind == "capability-packet-candidate"
    assert not contract.settled

    development = verify_agent_message(message)
    assert development.accepted
    assert development.message_contract_valid
    assert development.nonce_status == "consumed"
    assert development.candidate_packet_ids
    assert not development.quarantine_recommended
    assert development.packets[0].issuer_agent_id == "agent:alice"

    production = verify_agent_message(message, GeneralIntakePolicy(profile="production"))
    assert not production.accepted
    assert production.signature_required
    assert "signed agent message required" in "; ".join(production.reasons)

    signed_shape = message.model_copy(
        update={
            "issuer_public_key_id": "key:alice",
            "issuer_attestation_id": "attestation:alice",
            "signature_ref": "signature:alice:message",
        }
    )
    missing_context = verify_agent_message(
        signed_shape,
        GeneralIntakePolicy(profile="production"),
    )
    assert not missing_context.accepted
    assert "identity context" in "; ".join(missing_context.reasons)

    context = AgentMessageVerificationContext(
        profile="production",
        accepted=True,
        accepted_agent_ids=["agent:alice"],
        accepted_public_key_ids=["key:alice"],
    )
    accepted_signed = verify_agent_message(
        signed_shape,
        GeneralIntakePolicy(profile="production"),
        context,
    )
    assert accepted_signed.accepted
    assert accepted_signed.identity_verified
    assert accepted_signed.consumed_nonces == ["nonce-1"]

    replay = verify_agent_message(
        signed_shape,
        GeneralIntakePolicy(
            profile="production",
            seen_message_nonces=["nonce-1"],
        ),
        context,
    )
    assert replay.replay_detected
    assert not replay.accepted
    assert replay.nonce_status == "replayed"
    assert replay.nonce_ledger.replayed_nonces == ["nonce-1"]

    inbox_path = tmp_path / "inbox.json"
    inbox = append_agent_message(inbox_path, signed_shape)
    assert read_agent_inbox(inbox_path).messages == inbox.messages
    inbox_report = ingest_agent_inbox(str(inbox_path), GeneralIntakePolicy(profile="development"))
    assert inbox_report.accepted

    list_inbox = tmp_path / "list-inbox.json"
    list_inbox.write_text(
        json.dumps([signed_shape.model_dump(mode="json")]),
        encoding="utf-8",
    )
    assert ingest_agent_inbox(str(list_inbox)).accepted

    jsonl_inbox = tmp_path / "inbox.jsonl"
    jsonl_inbox.write_text(signed_shape.model_dump_json() + "\n", encoding="utf-8")
    assert isinstance(read_agent_inbox(jsonl_inbox), AgentInboxRecord)


def test_agent_message_digest_mismatch_rejects() -> None:
    message = AgentMessageEnvelope(
        message_id="agent-message:bad-digest",
        sender_agent_id="agent:alice",
        content="changed",
        content_sha256="0" * 64,
    )
    report = verify_agent_message(message)
    assert not report.accepted
    assert "digest mismatch" in report.reasons[0]


def test_agent_message_time_and_identity_context_fail_closed() -> None:
    expired = AgentMessageEnvelope(
        message_id="agent-message:expired",
        sender_agent_id="agent:alice",
        content="expired packet",
        content_sha256=sha256_text("expired packet"),
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2026-01-02T00:00:00Z",
        nonce="nonce-expired",
        issuer_public_key_id="key:alice",
        issuer_attestation_id="attestation:alice",
        signature_ref="signature:alice:expired",
    )
    report = verify_agent_message(
        expired,
        GeneralIntakePolicy(profile="production"),
        AgentMessageVerificationContext(
            profile="production",
            accepted=True,
            accepted_agent_ids=["agent:alice"],
            accepted_public_key_ids=["key:alice"],
        ),
    )
    assert not report.accepted
    assert "expired" in "; ".join(report.reasons)

    wrong_context = AgentMessageVerificationContext(
        profile="production",
        accepted=True,
        accepted_agent_ids=["agent:bob"],
        accepted_public_key_ids=["key:bob"],
    )
    active = expired.model_copy(update={"expires_at": "2099-01-02T00:00:00Z"})
    identity_reject = verify_agent_message(
        active,
        GeneralIntakePolicy(profile="production"),
        wrong_context,
    )
    assert not identity_reject.accepted
    assert identity_reject.identity_reasons

    invalid_time = active.model_copy(update={"issued_at": "not-a-time"})
    invalid_time_report = verify_agent_message(
        invalid_time,
        GeneralIntakePolicy(profile="production"),
        AgentMessageVerificationContext(
            profile="production",
            accepted=True,
            accepted_agent_ids=["agent:alice"],
            accepted_public_key_ids=["key:alice"],
        ),
    )
    assert "issued_at is not valid" in "; ".join(invalid_time_report.reasons)

    future = active.model_copy(update={"issued_at": "2099-01-01T00:00:00Z"})
    future_report = verify_agent_message(
        future,
        GeneralIntakePolicy(profile="production", max_message_clock_skew_seconds=0),
        AgentMessageVerificationContext(
            profile="production",
            accepted=True,
            accepted_agent_ids=["agent:alice"],
            accepted_public_key_ids=["key:alice"],
        ),
    )
    assert "future clock skew" in "; ".join(future_report.reasons)

    missing_key = active.model_copy(update={"issuer_public_key_id": None})
    missing_key_report = verify_agent_message(
        missing_key,
        GeneralIntakePolicy(profile="production"),
        AgentMessageVerificationContext(
            profile="production",
            accepted=True,
            accepted_agent_ids=["agent:alice"],
            accepted_public_key_ids=["key:alice"],
        ),
    )
    assert "issuer_public_key_id is required" in "; ".join(missing_key_report.identity_reasons)

    attestation_reject = verify_agent_message(
        active,
        GeneralIntakePolicy(profile="production"),
        AgentMessageVerificationContext(
            profile="production",
            accepted=True,
            accepted_agent_ids=["agent:alice"],
            accepted_public_key_ids=["key:alice"],
            accepted_attestation_ids=["attestation:other"],
        ),
    )
    assert "issuer_attestation_id" in "; ".join(attestation_reject.identity_reasons)
