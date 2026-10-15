# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.pidginhost.cloud.plugins.modules import kubernetes_cluster_upgrade as module

CLUSTER = "/api/kubernetes/clusters/7/"
KUBE = CLUSTER + "kube-version-upgrade/"
TALOS = CLUSTER + "talos-version-upgrade/"
FEATURE = CLUSTER + "upgrade-feature/"
LB = CLUSTER + "upgrade-lb/"


def cluster(**kw):
    base = {"id": 7, "name": "prod", "status": "active", "features_ready": True, "kube_version": "1.35.7",
            "talos_upgrade_available": False, "talos_version": "v1.12.0"}
    base.update(kw)
    return base


def refusal(field, text):
    return {"message": "Validation error", "extra": {"fields": {field: [text]}}}


def plan(convergence="action_required", can_execute=True, actions=("replace_envoy",), blockers=()):
    return {"inspection_id": "a1b2", "convergence": convergence, "level": 1 if can_execute else None,
            "actions": list(actions), "blockers": list(blockers), "can_execute": can_execute}


def test_upgrades_kubernetes_and_waits(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster(status="upgrading"))
    api.add("GET", CLUSTER, cluster(kube_version="1.36.3"))
    api.add("POST", KUBE, {"status": "OK"})

    result = run(module, cluster_id=7, component="kubernetes")

    assert not result.failed, result.result
    assert result.changed
    assert result["cluster"]["kube_version"] == "1.36.3"
    assert result["result"] == {"status": "OK"}
    assert api.writes() == [("POST", KUBE, {})]


def test_kubernetes_at_latest_version_is_unchanged(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", KUBE, refusal("non_field_errors", "You are running the latest version available."), status=400)

    result = run(module, cluster_id=7, component="kubernetes")

    assert not result.failed, result.result
    assert not result.changed


def test_other_kubernetes_refusal_fails(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", KUBE, refusal("non_field_errors", "Invalid status for resource."), status=400)

    result = run(module, cluster_id=7, component="kubernetes")

    assert result.failed
    assert not result.changed
    assert result["status_code"] == 400
    assert "Invalid status for resource." in result["msg"]


def test_kubernetes_check_mode_makes_no_writes(api, run):
    api.add("GET", CLUSTER, cluster())

    result = run(module, check_mode=True, cluster_id=7, component="kubernetes")

    assert result.changed
    assert api.writes() == []


def test_waits_for_running_upgrade_before_deciding(api, run):
    api.add("GET", "/api/kubernetes/clusters/",
            {"count": 1, "next": None, "previous": None, "results": [cluster(status="upgrading")]})
    api.add("GET", CLUSTER, cluster(status="upgrading", talos_upgrade_available=True))
    api.add("GET", CLUSTER, cluster())

    result = run(module, cluster_name="prod", component="talos")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == []


def test_upgrades_talos_when_available(api, run):
    api.add("GET", CLUSTER, cluster(talos_upgrade_available=True))
    api.add("GET", CLUSTER, cluster(status="upgrading"))
    api.add("GET", CLUSTER, cluster(talos_version="v1.12.1"))
    api.add("POST", TALOS, {"status": "OK"})

    result = run(module, cluster_id=7, component="talos")

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", TALOS, {})]


def test_upgrade_failure_fails(api, run):
    api.add("GET", CLUSTER, cluster(talos_upgrade_available=True))
    api.add("GET", CLUSTER, cluster(status="failed"))
    api.add("POST", TALOS, {"status": "OK"})

    result = run(module, cluster_id=7, component="talos")

    assert result.failed
    assert result.changed


def test_upgrades_feature(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster(features_ready=False))
    api.add("GET", CLUSTER, cluster())
    api.add("POST", FEATURE, {"status": "OK", "message": "Retrying cert-manager installation..."})

    result = run(module, cluster_id=7, component="feature", feature="cert-manager", retry=True)

    assert not result.failed, result.result
    assert result.changed
    assert api.writes() == [("POST", FEATURE, {"feature_name": "cert-manager", "retry": True})]


def test_feature_without_upgrade_is_unchanged(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", FEATURE, refusal("feature_name", "No upgrade available or not compatible."), status=400)

    result = run(module, cluster_id=7, component="feature", feature="cert-manager")

    assert not result.failed, result.result
    assert not result.changed


def test_feature_component_requires_feature(api, run):
    result = run(module, cluster_id=7, component="feature")

    assert result.failed
    assert api.calls == []


def test_retry_requires_feature_component(api, run):
    result = run(module, cluster_id=7, component="talos", retry=True)

    assert result.failed
    assert api.calls == []


def test_load_balancer_current_is_unchanged(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan("current", can_execute=False, actions=()))

    result = run(module, cluster_id=7, component="load_balancer")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == [("POST", LB, {"dry_run": True})]


def test_load_balancer_blockers_fail(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan("manual_review", can_execute=False, actions=(), blockers=("not_inspected",)))

    result = run(module, cluster_id=7, component="load_balancer")

    assert result.failed
    assert not result.changed
    assert "not_inspected" in result["msg"]
    assert api.writes() == [("POST", LB, {"dry_run": True})]


def test_load_balancer_upgrade_runs_the_dry_run_plan(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("GET", CLUSTER, cluster(features_ready=False))
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan())
    api.add("POST", LB, {"operation_id": "9", "status": "planned"}, status=202)
    api.add("POST", LB, plan("operation_in_progress", can_execute=False, actions=()))
    api.add("POST", LB, plan("current", can_execute=False, actions=()))

    result = run(module, cluster_id=7, component="load_balancer")

    assert not result.failed, result.result
    assert result.changed
    assert result["result"] == {"operation_id": "9", "status": "planned"}
    assert api.writes() == [("POST", LB, {"dry_run": True}), ("POST", LB, {"inspection_id": "a1b2"}),
                            ("POST", LB, {"dry_run": True}), ("POST", LB, {"dry_run": True})]


def test_load_balancer_check_mode_only_runs_the_dry_run(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan())

    result = run(module, check_mode=True, cluster_id=7, component="load_balancer")

    assert result.changed
    assert result["result"]["inspection_id"] == "a1b2"
    assert api.writes() == [("POST", LB, {"dry_run": True})]


@pytest.mark.parametrize("component,endpoint", [("kubernetes", KUBE), ("talos", TALOS)])
def test_active_cluster_with_unchanged_version_is_not_success(api, run, component, endpoint):
    api.add("GET", CLUSTER, cluster(talos_upgrade_available=True))
    api.add("GET", CLUSTER, cluster(status="upgrading"))
    api.add("GET", CLUSTER, cluster())
    api.add("POST", endpoint, {"status": "OK"})

    result = run(module, cluster_id=7, component=component)

    assert result.failed
    assert result.changed
    assert "installed version" in result["msg"]


@pytest.mark.parametrize("body", ["Upgrade unavailable", ["Upgrade unavailable"], {"extra": "Unavailable"}])
def test_unexpected_refusal_shape_is_a_clean_failure(api, run, body):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", KUBE, body, status=400)

    result = run(module, cluster_id=7, component="kubernetes")

    assert result.failed
    assert not result.changed
    assert result["status_code"] == 400


def test_load_balancer_wait_does_not_trust_active_cluster(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan())
    api.add("POST", LB, {"operation_id": "9", "status": "planned"}, status=202)
    api.add("POST", LB, plan("operation_in_progress", can_execute=False, actions=()))

    result = run(module, cluster_id=7, component="load_balancer", timeout=0)

    assert result.failed
    assert result.changed
    assert "in time" in result["msg"]


def test_load_balancer_waits_for_existing_job_without_starting_another(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan("operation_in_progress", can_execute=False, actions=()))
    api.add("POST", LB, plan("current", can_execute=False, actions=()))

    result = run(module, cluster_id=7, component="load_balancer")

    assert not result.failed, result.result
    assert not result.changed
    assert api.writes() == [("POST", LB, {"dry_run": True}), ("POST", LB, {"dry_run": True})]


def test_load_balancer_poll_error_keeps_changed(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan())
    api.add("POST", LB, {"operation_id": "9", "status": "planned"}, status=202)
    api.add("POST", LB, plan("operation_in_progress", can_execute=False, actions=()))
    api.add("POST", LB, {"message": "Unavailable"}, status=503)

    result = run(module, cluster_id=7, component="load_balancer")

    assert result.failed
    assert result.changed


def test_load_balancer_failed_dispatch_cannot_report_success(api, run):
    api.add("GET", CLUSTER, cluster())
    api.add("POST", LB, plan())
    api.add("POST", LB, {"operation_id": "9", "status": "planned"}, status=202)
    api.add("POST", LB, plan())

    result = run(module, cluster_id=7, component="load_balancer", timeout=0)

    assert result.failed
    assert result.changed
