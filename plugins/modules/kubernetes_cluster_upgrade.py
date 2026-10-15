# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_cluster_upgrade

short_description: Upgrade a Kubernetes cluster component.

version_added: 0.4.0

description:
  - Upgrade one component of a PidginHost Kubernetes cluster to the next version the platform offers.
  - V(kubernetes) and V(talos) move one version at a time. Run the task again to go further.
  - Nothing changes when the component is already current. For V(kubernetes) and V(feature) only the upgrade request
    tells, so in check mode they always report a change.
  - V(load_balancer) first asks the API for its upgrade plan, also in check mode. The module fails when the plan
    cannot run, listing the blockers.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_kube_version_upgrade_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  cluster_id:
    description:
      - ID of the cluster.
    type: int
  cluster_name:
    description:
      - Name of the cluster. Must be unique in the account.
    type: str
  component:
    description:
      - What to upgrade.
      - V(kubernetes) upgrades Kubernetes, V(talos) upgrades the Talos operating system of the nodes.
      - V(feature) upgrades the cluster feature named in O(feature) to the latest compatible version.
      - V(load_balancer) performs the load balancer upgrade the platform plans for the cluster.
    type: str
    choices: [kubernetes, talos, feature, load_balancer]
    required: true
  feature:
    description:
      - Feature to upgrade, for example V(cert-manager). Required when O(component=feature).
    type: str
  retry:
    description:
      - Retry a failed feature installation. Only valid with O(component=feature).
    type: bool
    default: false
  wait:
    description:
      - Wait until the cluster is active with its features ready again, and fail if the upgrade fails.
      - Also wait for an upgrade that is already running before starting another one.
      - The API does not report the progress of a feature upgrade that has not started yet, so for
        O(component=feature) the wait can end before the upgrade runs.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Upgrade Kubernetes by one version
  pidginhost.cloud.kubernetes_cluster_upgrade:
    cluster_name: prod
    component: kubernetes
    timeout: 3600

- name: Upgrade cert-manager
  pidginhost.cloud.kubernetes_cluster_upgrade:
    cluster_name: prod
    component: feature
    feature: cert-manager
"""

RETURN = r"""
cluster:
  description:
    - Cluster details. With O(wait=true) and a change, the details after the upgrade.
  returned: success
  type: dict
  sample:
    id: 7
    name: prod
    status: active
    kube_version: 1.36.3
    talos_upgrade_available: false
    features_ready: true
result:
  description:
    - API answer to the upgrade request, or the load balancer upgrade plan when nothing was started.
    - Empty when no request was needed.
  returned: success
  type: dict
  sample:
    operation_id: "9"
    status: planned
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec

# The API answers these 400 refusals when there is nothing to upgrade.
KUBE_LATEST = "You are running the latest version available."
NO_FEATURE_UPGRADE = "No upgrade available or not compatible."


def settled(cluster):
    return cluster["status"] == "failed" or (cluster["status"] == "active" and cluster["features_ready"])


def wait_settled(api, module, cluster, changed):
    # Kubernetes and Talos upgrades set the cluster to upgrading; feature and load balancer upgrades clear
    # features_ready while they run.
    path = "%s%s/" % (CLUSTERS, cluster["id"])
    done = api.wait_for(lambda: api.get(path), settled)
    if not done or done["status"] != "active":
        module.fail_json(
            changed=changed,
            msg="Kubernetes cluster %s %s." % (cluster["id"], "is failed" if done else "did not settle in time"),
            cluster=done or cluster,
        )
    return done


def post_upgrade(api, module, path, body, nothing_to_do):
    """POST an upgrade. Returns (changed, response); a refusal saying there is nothing to do is no change."""
    response = api.post(path, body, allow_status=(400,))
    if api.status != 400:
        return True, response
    fields = (response.get("extra") or {}).get("fields") or {}
    if any(nothing_to_do in messages for messages in fields.values()):
        return False, response
    module.fail_json(msg="The upgrade was refused: %s" % (fields or response.get("message")),
                     status_code=400, response=response)


def upgrade_load_balancer(api, module, path):
    plan = api.post(path, {"dry_run": True})
    api.changed = False  # A dry run changes nothing.
    if plan["convergence"] in ("current", "operation_in_progress"):
        return False, plan
    # A plan may carry blockers next to an executable level; the API decides with can_execute.
    if not plan["can_execute"]:
        module.fail_json(
            msg="The load balancer upgrade cannot run (%s). Blockers: %s."
                % (plan["convergence"], ", ".join(plan["blockers"]) or "none"),
            result=plan,
        )
    if module.check_mode:
        return True, plan
    return True, api.post(path, {"inspection_id": plan["inspection_id"]})


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            component=dict(type="str", choices=["kubernetes", "talos", "feature", "load_balancer"], required=True),
            feature=dict(type="str"),
            retry=dict(type="bool", default=False),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        mutually_exclusive=[("cluster_id", "cluster_name")],
        required_if=[("component", "feature", ["feature"])],
        supports_check_mode=True,
    )
    params = module.params
    component = params["component"]
    if params["retry"] and component != "feature":
        module.fail_json(msg="retry requires component=feature.")
    api = PidginHostAPI(module)
    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    if params["wait"] and not module.check_mode and not settled(cluster):
        cluster = wait_settled(api, module, cluster, changed=False)

    path = "%s%s/" % (CLUSTERS, cluster["id"])
    if component == "load_balancer":
        changed, result = upgrade_load_balancer(api, module, path + "upgrade-lb/")
    elif component == "talos" and not cluster["talos_upgrade_available"]:
        changed, result = False, {}
    elif module.check_mode:
        changed, result = True, {}
    elif component == "talos":
        changed, result = True, api.post(path + "talos-version-upgrade/")
    elif component == "kubernetes":
        changed, result = post_upgrade(api, module, path + "kube-version-upgrade/", None, KUBE_LATEST)
    else:
        changed, result = post_upgrade(api, module, path + "upgrade-feature/",
                                       {"feature_name": params["feature"], "retry": params["retry"]},
                                       NO_FEATURE_UPGRADE)

    if changed and params["wait"] and not module.check_mode:
        cluster = wait_settled(api, module, cluster, changed=True)
    module.exit_json(changed=changed, cluster=cluster, result=result)


if __name__ == "__main__":
    main()
