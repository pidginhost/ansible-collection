# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_cluster as module

CLUSTERS = "/api/kubernetes/clusters/"
CLUSTER = CLUSTERS + "7/"


def cluster(**kw):
    base = {"id": 7, "name": "prod", "status": "active", "cluster_type": "prod", "kube_version": "1.35.7",
            "features": ["cert-manager", "metrics-server"], "features_ready": True, "protected": False,
            "price_per_month": "100.0000"}
    base.update(kw)
    return base


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def test_creates_cluster_and_waits_until_active(api, run):
    api.add("GET", CLUSTERS, page(cluster(id=6, name="dev")))
    api.add("POST", CLUSTERS, {"id": 7}, status=201)
    api.add("GET", CLUSTER, None, status=404)
    api.add("GET", CLUSTER, cluster(status="provisioning"))
    api.add("GET", CLUSTER, cluster())

    result = run(module, name="prod", cluster_type="prod", resource_pool_package="k8s-w2", resource_pool_size=3,
                 features=["cert-manager", "metrics-server"], kube_version="1.35.7")

    assert not result.failed, result.result
    assert result.changed
    assert result["cluster"]["status"] == "active"
    assert api.writes() == [("POST", CLUSTERS, {
        "name": "prod", "cluster_type": "prod", "resource_pool_package": "k8s-w2", "resource_pool_size": 3,
        "features": ["cert-manager", "metrics-server"], "kube_version": "1.35.7"})]


def test_create_turns_default_protection_off_when_asked(api, run):
    api.add("GET", CLUSTERS, page())
    api.add("POST", CLUSTERS, {"id": 7}, status=201)
    api.add("GET", CLUSTER, cluster(protected=True))
    api.add("PATCH", CLUSTER, cluster(protected=False))

    result = run(module, name="prod", cluster_type="prod", resource_pool_package="k8s-w2", protected=False)

    assert not result.failed, result.result
    assert result["cluster"]["protected"] is False
    assert api.writes()[1] == ("PATCH", CLUSTER, {"protected": False})


def test_create_without_wait_returns_id(api, run):
    api.add("GET", CLUSTERS, page())
    api.add("POST", CLUSTERS, {"id": 7}, status=201)

    result = run(module, name="prod", cluster_type="dev", resource_pool_package="k8s-w2", wait=False)

    assert result.changed
    assert result["cluster"] == {"id": 7}


def test_create_requires_type_and_package(api, run):
    api.add("GET", CLUSTERS, page())

    result = run(module, name="prod")

    assert result.failed
    assert "cluster_type, resource_pool_package" in result["msg"]
    assert api.writes() == []


def test_create_fails_when_provisioning_fails(api, run):
    api.add("GET", CLUSTERS, page())
    api.add("POST", CLUSTERS, {"id": 7}, status=201)
    api.add("GET", CLUSTER, cluster(status="failed"))

    result = run(module, name="prod", cluster_type="dev", resource_pool_package="k8s-w2")

    assert result.failed
    assert result.changed
    assert "failed to provision" in result["msg"]


def test_create_check_mode_makes_no_writes(api, run):
    api.add("GET", CLUSTERS, page())

    result = run(module, check_mode=True, name="prod", cluster_type="dev", resource_pool_package="k8s-w2")

    assert result.changed
    assert api.writes() == []


def test_existing_cluster_is_unchanged_and_features_compare_as_set(api, run):
    api.add("GET", CLUSTERS, page(cluster()))

    result = run(module, name="prod", cluster_type="dev", resource_pool_package="other", kube_version="1.36.3",
                 features=["metrics-server", "cert-manager"], protected=False)

    assert not result.failed, result.result
    assert not result.changed
    assert result["cluster"]["id"] == 7
    assert api.writes() == []


def test_updates_features_and_protection_in_one_patch(api, run):
    api.add("GET", CLUSTERS, page(cluster()))
    api.add("PATCH", CLUSTER, cluster(features=["ceph-csi"], protected=True))

    result = run(module, name="prod", features=["ceph-csi"], protected=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["cluster"]["features"] == ["ceph-csi"]
    assert api.writes() == [("PATCH", CLUSTER, {"features": ["ceph-csi"], "protected": True})]


def test_waits_for_features_ready_before_changing_them(api, run):
    api.add("GET", CLUSTERS, page(cluster(features_ready=False)))
    api.add("GET", CLUSTER, cluster(features_ready=False))
    api.add("GET", CLUSTER, cluster())
    api.add("PATCH", CLUSTER, cluster(features=[]))

    result = run(module, name="prod", features=[])

    assert not result.failed, result.result
    assert result.changed
    assert len(api.requests("GET", CLUSTER)) == 2
    assert api.writes() == [("PATCH", CLUSTER, {"features": []})]


def test_renames_only_when_found_by_id(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("PATCH", CLUSTER, cluster(name="staging"))

    result = run(module, cluster_id=7, name="staging")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("PATCH", CLUSTER, {"name": "staging"})]


def test_update_check_mode_makes_no_writes(api, run):
    api.add("GET", CLUSTERS, page(cluster()))

    result = run(module, check_mode=True, name="prod", protected=True)

    assert result.changed
    assert api.writes() == []


def test_missing_cluster_id_fails(api, run):
    api.add("GET", CLUSTER, None, status=404)

    result = run(module, cluster_id=7)

    assert result.failed
    assert "not found" in result["msg"]


def test_cluster_being_deleted_cannot_be_updated(api, run):
    api.add("GET", CLUSTERS, page(cluster(status="cancelling")))

    result = run(module, name="prod", protected=True)

    assert result.failed
    assert api.writes() == []


def test_absent_deletes_and_waits_until_gone(api, run):
    api.add("GET", CLUSTERS, page(cluster()))
    api.add("DELETE", CLUSTER, None, status=204)
    api.add("GET", CLUSTER, cluster(status="cancelling"))
    api.add("GET", CLUSTER, None, status=404)

    result = run(module, state="absent", name="prod")

    assert not result.failed, result.result
    assert result.changed
    assert result["cluster"]["id"] == 7
    assert api.writes() == [("DELETE", CLUSTER, None)]


def test_absent_protected_cluster_fails_without_protected_false(api, run):
    api.add("GET", CLUSTERS, page(cluster(protected=True)))

    result = run(module, state="absent", name="prod")

    assert result.failed
    assert not result.changed
    assert "protected=false" in result["msg"]
    assert api.writes() == []


def test_absent_turns_protection_off_first(api, run):
    api.add("GET", CLUSTERS, page(cluster(protected=True)))
    api.add("PATCH", CLUSTER, cluster(protected=False))
    api.add("DELETE", CLUSTER, None, status=204)

    result = run(module, state="absent", name="prod", protected=False, wait=False)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("PATCH", CLUSTER, {"protected": False}), ("DELETE", CLUSTER, None)]


def test_absent_fails_when_delete_fails(api, run):
    api.add("GET", CLUSTERS, page(cluster()))
    api.add("DELETE", CLUSTER, None, status=204)
    api.add("GET", CLUSTER, cluster(status="failed"))

    result = run(module, state="absent", name="prod")

    assert result.failed
    assert result.changed


def test_absent_check_mode_makes_no_writes(api, run):
    api.add("GET", CLUSTERS, page(cluster(protected=True)))

    result = run(module, check_mode=True, state="absent", name="prod", protected=False)

    assert result.changed
    assert api.writes() == []


def test_absent_already_cancelling_is_unchanged(api, run):
    api.add("GET", CLUSTERS, page(cluster(status="cancelling", protected=True)))

    result = run(module, state="absent", name="prod", wait=False)

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_absent_missing_cluster_is_ok(api, run):
    api.add("GET", CLUSTERS, page(cluster(name="dev")))

    result = run(module, state="absent", name="prod")

    assert not result.failed
    assert not result.changed
