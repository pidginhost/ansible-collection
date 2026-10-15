# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_cluster_encryption as module

CLUSTER = "/api/kubernetes/clusters/7/"
ENCRYPTION = CLUSTER + "encryption/"


def state(mode="none", status="disabled", op_status=None, requested="wireguard", reason="", error=""):
    operation = None
    if op_status:
        operation = {"id": 4, "kind": "toggle", "status": op_status, "requested_mode": requested,
                     "reason": reason, "message": error}
    return {"mode": mode, "status": status, "reason": reason, "error": error, "restart_required": False,
            "per_node": {}, "operation": operation}


def prepare(api, *states):
    api.add("GET", CLUSTER, {"id": 7, "name": "prod", "status": "active"})
    for item in states:
        api.add("GET", ENCRYPTION, item)


def test_enables_encryption_and_waits(api, run):
    prepare(api, state(), state(op_status="pending"), state(status="enabling", op_status="running"),
          state(mode="wireguard", status="enabled_restart_required", op_status="succeeded"))
    api.add("POST", ENCRYPTION, {"id": 4, "status": "pending", "requested_mode": "wireguard"}, status=202)

    result = run(module, cluster_id=7, mode="wireguard", acknowledge_workload_restart=True)

    assert not result.failed, result.result
    assert result.changed
    assert result["encryption"]["mode"] == "wireguard"
    assert api.writes() == [("POST", ENCRYPTION, {"mode": "wireguard", "acknowledge_workload_restart": True})]


def test_same_settled_mode_is_unchanged(api, run):
    prepare(api, state(mode="wireguard", status="enabled", op_status="succeeded"))

    result = run(module, cluster_id=7, mode="wireguard")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_change_already_running_is_unchanged_without_wait(api, run):
    prepare(api, state(status="enabling", op_status="running"))

    result = run(module, cluster_id=7, mode="wireguard", wait=False)

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_waits_for_running_change_before_comparing(api, run):
    prepare(api, state(status="enabling", op_status="running"),
          state(mode="wireguard", status="enabled", op_status="succeeded"))

    result = run(module, cluster_id=7, mode="wireguard")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_check_mode_makes_no_writes(api, run):
    prepare(api, state())

    result = run(module, check_mode=True, cluster_id=7, mode="wireguard", acknowledge_workload_restart=True)

    assert result.changed
    assert api.writes() == []


def test_refusal_is_reported_with_reason(api, run):
    prepare(api, state())
    api.add("POST", ENCRYPTION, {"reason": "workload_restart_ack_required",
                                 "message": "Confirm that workloads will be restarted."}, status=400)

    result = run(module, cluster_id=7, mode="wireguard")

    assert result.failed
    assert not result.changed
    assert "workload_restart_ack_required" in result["msg"]
    assert "Confirm that workloads" in result["msg"]
    assert result["status_code"] == 400
    assert api.writes() == [("POST", ENCRYPTION, {"mode": "wireguard", "acknowledge_workload_restart": False})]


def test_conflict_is_reported(api, run):
    prepare(api, state(mode="wireguard", status="enabled"))
    api.add("POST", ENCRYPTION, {"reason": "cluster_operation_in_progress", "message": "Busy."}, status=409)

    result = run(module, cluster_id=7, mode="none", acknowledge_workload_restart=True)

    assert result.failed
    assert "cluster_operation_in_progress" in result["msg"]


def test_failed_change_fails_with_reason(api, run):
    prepare(api, state(), state(op_status="pending"),
          state(status="disabled", op_status="failed", reason="kernel_wireguard_unavailable",
                error="WireGuard is not available."))
    api.add("POST", ENCRYPTION, {"id": 4, "status": "pending"}, status=202)

    result = run(module, cluster_id=7, mode="wireguard", acknowledge_workload_restart=True)

    assert result.failed
    assert result.changed
    assert "kernel_wireguard_unavailable" in result["msg"]


def test_wait_timeout_fails(api, run):
    prepare(api, state(), state(op_status="pending"))
    api.add("POST", ENCRYPTION, {"id": 4, "status": "pending"}, status=202)

    result = run(module, cluster_id=7, mode="wireguard", acknowledge_workload_restart=True, timeout=0)

    assert result.failed
    assert result.changed
    assert "in time" in result["msg"]


def test_failed_running_change_is_not_automatically_retried(api, run):
    prepare(api, state(status="enabling", op_status="running"),
          state(op_status="failed", reason="kernel_wireguard_unavailable", error="WireGuard unavailable."))

    result = run(module, cluster_id=7, mode="wireguard", acknowledge_workload_restart=True)

    assert result.failed
    assert not result.changed
    assert "kernel_wireguard_unavailable" in result["msg"]
    assert api.writes() == []


def test_failed_operation_is_reported_even_if_mode_matches(api, run):
    prepare(api, state(), state(mode="wireguard", status="enabled", op_status="failed",
                              reason="verification_failed", error="Verification failed."))
    api.add("POST", ENCRYPTION, {"id": 4, "status": "pending"}, status=202)

    result = run(module, cluster_id=7, mode="wireguard", acknowledge_workload_restart=True)

    assert result.failed
    assert result.changed
    assert "verification_failed" in result["msg"]
