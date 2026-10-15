# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_route as module

CLUSTER = "/api/kubernetes/clusters/7/"
HTTP = CLUSTER + "httproutes/"
TCP = CLUSTER + "tcproutes/"
UDP = CLUSTER + "udproutes/"


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def http_route(**kw):
    base = {"id": 4, "name": "web", "namespace": "default", "hostnames": ["example.com", "www.example.com"],
            "backend_service_name": "web", "backend_service_port": 80, "backend_namespace": "default",
            "path_prefix": "/", "enable_tls": True, "status_ready": True, "status_message": ""}
    base.update(kw)
    return base


def port_route(**kw):
    base = {"id": 5, "name": "dns", "namespace": "default", "port": 5353, "backend_service_name": "dns",
            "backend_service_port": 53, "backend_namespace": "default", "status_ready": True, "status_message": ""}
    base.update(kw)
    return base


PLATFORM = port_route(id=1, name="kube-apiserver", namespace="envoy-gw", port=0,
                      backend_service_name="kube-apiserver", backend_service_port=6443)


def setup(api):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})


def test_http_route_is_created(api, run):
    setup(api)
    api.add("GET", HTTP, page())
    api.add("POST", HTTP, http_route(), status=201)

    result = run(module, cluster_id=7, protocol="http", name="web", hostnames=["example.com"],
                 backend_service_name="web", backend_service_port=80, enable_tls=False)

    assert not result.failed, result.result
    assert result.changed
    assert result["route"]["id"] == 4
    assert api.writes() == [("POST", HTTP, {
        "name": "web", "namespace": "default", "hostnames": ["example.com"], "backend_service_name": "web",
        "backend_service_port": 80, "enable_tls": False})]


def test_http_route_with_reordered_hostnames_is_unchanged(api, run):
    setup(api)
    api.add("GET", HTTP, page(http_route(), http_route(id=6, namespace="shop")))

    result = run(module, cluster_id=7, protocol="http", name="web", hostnames=["www.example.com", "example.com"],
                 backend_service_name="web", backend_service_port=80, path_prefix="/", enable_tls=True)

    assert not result.failed, result.result
    assert not result.changed
    assert result["route"]["id"] == 4
    assert api.writes() == []


def test_http_route_patches_only_changed_fields(api, run):
    setup(api)
    api.add("GET", HTTP, page(http_route()))
    api.add("PATCH", HTTP + "4/", http_route(hostnames=["shop.example.com"], backend_service_port=8080))

    result = run(module, cluster_id=7, protocol="http", name="web", hostnames=["shop.example.com"],
                 backend_service_name="web", backend_service_port=8080)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [
        ("PATCH", HTTP + "4/", {"hostnames": ["shop.example.com"], "backend_service_port": 8080})]


def test_tcp_route_is_created_beside_platform_route(api, run):
    setup(api)
    api.add("GET", TCP, page(PLATFORM))
    api.add("POST", TCP, port_route(), status=201)

    result = run(module, cluster_id=7, protocol="tcp", name="dns", port=5353, backend_service_name="dns",
                 backend_service_port=53)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", TCP, {
        "name": "dns", "namespace": "default", "port": 5353, "backend_service_name": "dns",
        "backend_service_port": 53})]


def test_udp_route_port_is_patched(api, run):
    setup(api)
    api.add("GET", UDP, page(port_route(namespace="infra")))
    api.add("PATCH", UDP + "5/", port_route(namespace="infra", port=5354))

    result = run(module, cluster_id=7, protocol="udp", name="dns", namespace="infra", port=5354,
                 backend_namespace="default")

    assert not result.failed, result.result
    assert result.changed
    assert result["route"]["port"] == 5354
    assert api.writes() == [("PATCH", UDP + "5/", {"port": 5354})]


def test_route_is_deleted(api, run):
    setup(api)
    api.add("GET", TCP, page(PLATFORM, port_route()))
    api.add("DELETE", TCP + "5/", None, status=204)

    result = run(module, cluster_id=7, protocol="tcp", name="dns", state="absent")

    assert not result.failed, result.result
    assert result.changed
    assert result["route"]["id"] == 5
    assert api.writes() == [("DELETE", TCP + "5/", None)]


def test_missing_route_is_unchanged_when_absent(api, run):
    setup(api)
    api.add("GET", TCP, page(PLATFORM))

    result = run(module, cluster_id=7, protocol="tcp", name="dns", state="absent")

    assert not result.failed, result.result
    assert not result.changed
    assert result["route"] == {}


def test_check_mode_makes_no_writes(api, run):
    setup(api)
    api.add("GET", HTTP, page(http_route()))

    created = run(module, check_mode=True, cluster_id=7, protocol="http", name="api", hostnames=["example.com"],
                  backend_service_name="api", backend_service_port=80)
    changed = run(module, check_mode=True, cluster_id=7, protocol="http", name="web", enable_tls=False)
    deleted = run(module, check_mode=True, cluster_id=7, protocol="http", name="web", state="absent")

    assert created.changed and changed.changed and deleted.changed
    assert api.writes() == []


def test_options_of_another_protocol_fail(api, run):
    tcp = run(module, cluster_id=7, protocol="tcp", name="dns", port=53, hostnames=["example.com"])
    http = run(module, cluster_id=7, protocol="http", name="web", port=80)

    assert tcp.failed and "hostnames" in tcp["msg"]
    assert http.failed and "port" in http["msg"]
    assert api.calls == []


def test_create_requires_backend_and_port(api, run):
    setup(api)
    api.add("GET", UDP, page())

    result = run(module, cluster_id=7, protocol="udp", name="dns", backend_service_name="dns")

    assert result.failed
    assert "port" in result["msg"] and "backend_service_port" in result["msg"]
    assert api.writes() == []
