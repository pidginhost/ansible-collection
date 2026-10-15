# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_resource_pool as module

CLUSTER = "/api/kubernetes/clusters/7/"
POOLS = CLUSTER + "resource-pools/"
JOURNALS = CLUSTER + "pool-removal-journals/"


def cluster(status="active"):
    return {"id": 7, "name": "prod", "status": status}


def pool(size=2, **kw):
    base = {"id": 3, "package": "k8s-w2", "generation": "gen3", "size": size,
            "nodes": [{"id": 10 + i, "name": "w%d" % i, "ip": "192.0.2.%d" % (10 + i)} for i in range(size)]}
    base.update(kw)
    return base


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


def journal(journal_id, status, kind="downsize", message="", names=None, size=1):
    if names is None:
        names = ["w0", "w1"] if kind == "pool_delete" else ["w1"]
    return {"id": journal_id, "kind": kind, "status": status, "reason": "", "message": message,
            "items": [{"target_hostname": name} for name in names], "allowed_actions": [],
            "requested_pool_size": None if kind == "pool_delete" else size}


def test_creates_pool_and_waits_for_cluster(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster("upgrading"))
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool(id=2, package="k8s-w4")))
    api.add("POST", POOLS, {"id": 3}, status=201)
    api.add("GET", POOLS + "3/", pool())

    result = run(module, cluster_id=7, package="k8s-w2", size=2)

    assert not result.failed, result.result
    assert result.changed
    assert result["resource_pool"]["size"] == 2
    assert api.writes() == [("POST", POOLS, {"resource_pool_package": "k8s-w2", "resource_pool_size": 2})]


def test_matching_pool_is_unchanged(api, run):
    api.add("GET", "/api/kubernetes/clusters/", page(cluster()))
    api.add("GET", POOLS, page(pool(id=2, generation="gen2"), pool()))

    result = run(module, cluster_name="prod", package="k8s-w2", generation="gen3", size=2)

    assert not result.failed, result.result
    assert not result.changed
    assert result["resource_pool"]["id"] == 3
    assert api.writes() == []


def test_upsize_patches_and_waits(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster("upgrading"))
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool()))
    api.add("PATCH", POOLS + "3/", pool())
    api.add("GET", POOLS + "3/", pool(size=3))

    result = run(module, cluster_id=7, package="k8s-w2", size=3)

    assert not result.failed, result.result
    assert result.changed
    assert result["resource_pool"]["size"] == 3
    assert api.writes() == [("PATCH", POOLS + "3/", {"new_size": 3, "local_data_loss_accepted": False})]


def test_downsize_waits_for_removal_journal(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "3/", pool())
    api.add("GET", POOLS + "3/", pool(size=1))
    api.add("GET", JOURNALS, page(journal(4, "succeeded")))
    api.add("GET", JOURNALS, page(journal(5, "destructive"), journal(4, "succeeded")))
    api.add("GET", JOURNALS, page(journal(5, "succeeded"), journal(4, "succeeded")))
    api.add("PATCH", POOLS + "3/", pool())

    result = run(module, cluster_id=7, pool_id=3, size=1, local_data_loss_accepted=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["resource_pool"]["size"] == 1
    assert api.writes() == [("PATCH", POOLS + "3/", {"new_size": 1, "local_data_loss_accepted": True})]


def test_downsize_fails_when_journal_needs_attention(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "3/", pool())
    api.add("GET", JOURNALS, page())
    api.add("GET", JOURNALS, page(journal(1, "needs_attention", message="A worker could not be uncordoned.")))
    api.add("PATCH", POOLS + "3/", pool())

    result = run(module, cluster_id=7, pool_id=3, size=1, local_data_loss_accepted=True)

    assert result.failed
    assert result.changed
    assert "needs_attention" in result["msg"]
    assert "could not be uncordoned" in result["msg"]


def test_check_mode_makes_no_writes(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool()))

    created = run(module, check_mode=True, cluster_id=7, package="k8s-w4", size=1)
    resized = run(module, check_mode=True, cluster_id=7, package="k8s-w2", size=5)
    deleted = run(module, check_mode=True, cluster_id=7, package="k8s-w2", state="absent")

    assert created.changed and resized.changed and deleted.changed
    assert api.writes() == []


def test_deletes_pool_with_nodes_through_journal(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool()))
    api.add("GET", JOURNALS, page())
    api.add("GET", JOURNALS, page(journal(1, "succeeded", kind="pool_delete")))
    api.add("DELETE", POOLS + "3/", None, status=204)

    result = run(module, cluster_id=7, package="k8s-w2", state="absent", local_data_loss_accepted=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["resource_pool"]["id"] == 3
    assert api.writes() == [("DELETE", POOLS + "3/", {"local_data_loss_accepted": True})]


def test_deletes_empty_pool_and_waits_for_cluster(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster("upgrading"))
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool(size=0)))
    api.add("DELETE", POOLS + "3/", None, status=204)

    result = run(module, cluster_id=7, package="k8s-w2", state="absent")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("DELETE", POOLS + "3/", {"local_data_loss_accepted": False})]


def test_absent_pool_is_unchanged(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool()))

    result = run(module, cluster_id=7, package="k8s-w4", state="absent")

    assert not result.failed, result.result
    assert not result.changed
    assert result["resource_pool"] == {}


def test_create_requires_size(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page())

    result = run(module, cluster_id=7, package="k8s-w2")

    assert result.failed
    assert "size" in result["msg"]
    assert api.writes() == []


def test_unknown_pool_id_fails(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "9/", None, status=404)

    result = run(module, cluster_id=7, pool_id=9, size=2)

    assert result.failed
    assert "not found" in result["msg"]


def test_upsize_fails_when_nodes_are_missing_after_the_change(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster("upgrading"))
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS, page(pool()))
    api.add("PATCH", POOLS + "3/", pool())
    api.add("GET", POOLS + "3/", pool())

    result = run(module, cluster_id=7, package="k8s-w2", size=3)

    assert result.failed
    assert result.changed
    assert "2 nodes instead of 3" in result["msg"]


def test_removal_waits_for_its_own_journal_across_pages(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "3/", pool())
    api.add("GET", POOLS + "3/", pool(size=1))
    api.add("GET", JOURNALS, page())
    newer = journal(2, "succeeded", names=["other-worker"])
    api.add("GET", JOURNALS, dict(page(newer), next="https://example.com/next"))
    api.add("GET", JOURNALS + "?page=2", page(journal(1, "destructive")))
    api.add("GET", JOURNALS + "?page=2", page(journal(1, "failed", message="Drain failed.")))
    api.add("PATCH", POOLS + "3/", pool())

    result = run(module, cluster_id=7, pool_id=3, size=1, local_data_loss_accepted=True)

    assert result.failed
    assert result.changed
    assert result["journal"]["id"] == 1
    assert "Drain failed" in result["msg"]
    assert len(api.requests("GET", JOURNALS + "?page=2")) == 2


def test_delete_does_not_accept_an_unrelated_successful_journal(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "3/", pool())
    api.add("GET", JOURNALS, page())
    api.add("GET", JOURNALS, page(journal(1, "succeeded", kind="pool_delete", names=["other1", "other2"])))
    api.add("DELETE", POOLS + "3/", status=204)

    result = run(module, cluster_id=7, pool_id=3, state="absent", local_data_loss_accepted=True, timeout=0)

    assert result.failed
    assert result.changed
    assert "in time" in result["msg"]


def test_no_wait_does_not_read_journals_or_accept_data_loss(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "3/", pool())
    api.add("PATCH", POOLS + "3/", pool())

    result = run(module, cluster_id=7, pool_id=3, size=1, wait=False)

    assert not result.failed, result.result
    assert api.writes() == [("PATCH", POOLS + "3/", {"new_size": 1, "local_data_loss_accepted": False})]
    assert api.requests("GET", JOURNALS) == []


def test_waits_for_existing_resize_and_does_not_resubmit(api, run):
    api.add("GET", CLUSTER, cluster("upgrading"))
    api.add("GET", CLUSTER, cluster("upgrading"))
    api.add("GET", CLUSTER, cluster())
    api.add("GET", POOLS + "3/", pool(size=3))

    result = run(module, cluster_id=7, pool_id=3, size=3)

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []
    assert len(api.requests("GET", CLUSTER)) == 3
