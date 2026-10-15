# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_clusters_info as module

CLUSTERS = "/api/kubernetes/clusters/"
CLUSTER = CLUSTERS + "7/"


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def test_lists_every_cluster(api, run):
    api.add("GET", CLUSTERS, page({"id": 6, "name": "dev"}, {"id": 7, "name": "prod"}))

    result = run(module)

    assert not result.failed, result.result
    assert not result.changed
    assert [c["id"] for c in result["clusters"]] == [6, 7]


def test_one_cluster_with_includes(api, run):
    api.add("GET", CLUSTERS, page({"id": 6, "name": "dev"}, {"id": 7, "name": "prod"}))
    api.add("GET", CLUSTER + "resource-pools/", page({"id": 3, "package": "k8s-w2", "size": 2}))
    api.add("GET", CLUSTER + "httproutes/", page())
    api.add("GET", CLUSTER + "tcproutes/", page({"id": 1, "name": "kube-apiserver"}))
    api.add("GET", CLUSTER + "pool-removal-journals/", page())
    api.add("GET", CLUSTER + "connected-vms/", {"vms": [{"id": 5, "hostname": "web1.example.com"}]})
    api.add("GET", CLUSTER + "encryption/", {"mode": "none", "status": "disabled"})

    result = run(module, cluster_name="prod", include=[
        "resource_pools", "http_routes", "tcp_routes", "pool_removal_journals", "connected_vms", "encryption"])

    assert not result.failed, result.result
    (cluster,) = result["clusters"]
    assert cluster["id"] == 7
    assert cluster["resource_pools"][0]["id"] == 3
    assert cluster["http_routes"] == []
    assert cluster["tcp_routes"][0]["name"] == "kube-apiserver"
    assert cluster["pool_removal_journals"] == []
    assert cluster["connected_vms"] == [{"id": 5, "hostname": "web1.example.com"}]
    assert cluster["encryption"]["mode"] == "none"


def test_one_cluster_by_id(api, run):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod"})
    api.add("GET", CLUSTER + "eligible-vms/", {"vms": []})

    result = run(module, cluster_id=7, include=["eligible_vms"])

    assert not result.failed, result.result
    assert result["clusters"] == [{"id": 7, "name": "prod", "eligible_vms": []}]


def test_include_requires_one_cluster(api, run):
    result = run(module, include=["encryption"])

    assert result.failed
    assert api.calls == []


def test_missing_cluster_fails(api, run):
    api.add("GET", CLUSTER, None, status=404)

    result = run(module, cluster_id=7)

    assert result.failed
    assert "not found" in result["msg"]
