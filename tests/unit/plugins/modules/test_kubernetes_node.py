# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_node as module

CLUSTER = "/api/kubernetes/clusters/7/"
NODES = CLUSTER + "resource-pools/3/nodes/"
OPS = CLUSTER + "node-operations/"


def page(*items):
    return {"count": len(items), "next": None, "previous": None, "results": list(items)}


NODE = {"id": 11, "name": "prod-w1", "ip": "192.0.2.11"}


def op(status, kind="reboot", **kw):
    base = {"id": 9, "kind": kind, "source": "api", "target_hostname": "prod-w1", "status": status, "reason": "",
            "message": "", "local_data_loss_accepted": True, "allowed_actions": []}
    base.update(kw)
    return base


def prepare(api):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    api.add("GET", NODES, page(NODE))


def test_reboot_waits_until_succeeded(api, run):
    prepare(api)
    api.add("POST", NODES + "11/reboot/", op("pending"), status=202)
    api.add("GET", OPS + "9/", op("draining"))
    api.add("GET", OPS + "9/", op("succeeded"))

    result = run(module, cluster_id=7, pool_id=3, node="prod-w1", state="rebooted", local_data_loss_accepted=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["operation"]["status"] == "succeeded"
    assert api.writes() == [("POST", NODES + "11/reboot/", {"local_data_loss_accepted": True})]


def test_delete_by_id_confirms_hostname(api, run):
    prepare(api)
    api.add("DELETE", NODES + "11/", op("pending", kind="delete"), status=202)

    result = run(module, cluster_id=7, pool_id=3, node="11", state="absent", wait=False)

    assert not result.failed, result.result
    assert result.changed
    assert result["operation"]["kind"] == "delete"
    assert api.writes() == [
        ("DELETE", NODES + "11/", {"local_data_loss_accepted": False, "confirm_hostname": "prod-w1"})]


def test_missing_node_is_unchanged_when_absent(api, run):
    prepare(api)

    result = run(module, cluster_id=7, pool_id=3, node="prod-w9", state="absent")

    assert not result.failed, result.result
    assert not result.changed
    assert result["operation"] == {}
    assert api.writes() == []


def test_check_mode_makes_no_writes(api, run):
    prepare(api)

    rebooted = run(module, check_mode=True, cluster_id=7, pool_id=3, node="prod-w1", state="rebooted")
    deleted = run(module, check_mode=True, cluster_id=7, pool_id=3, node="prod-w1", state="absent")

    assert rebooted.changed and deleted.changed
    assert api.writes() == []


def test_blocked_operation_fails_with_reason_and_actions(api, run):
    prepare(api)
    api.add("POST", NODES + "11/reboot/", op("pending"), status=202)
    api.add("GET", OPS + "9/", op("blocked", reason="pdb_blocked", message="A PodDisruptionBudget blocks the drain.",
                                  allowed_actions=["retry", "cancel"]))

    result = run(module, cluster_id=7, pool_id=3, node="prod-w1", state="rebooted", local_data_loss_accepted=True)

    assert result.failed
    assert result.changed
    assert "blocked" in result["msg"]
    assert "PodDisruptionBudget" in result["msg"]
    assert "retry, cancel" in result["msg"]
    assert result["operation"]["id"] == 9


def test_reboot_of_missing_node_fails(api, run):
    prepare(api)

    result = run(module, cluster_id=7, pool_id=3, node="prod-w9", state="rebooted")

    assert result.failed
    assert "not found" in result["msg"]
    assert api.writes() == []
