# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_cluster_encryption

short_description: Turn WireGuard encryption of Kubernetes cluster traffic on or off.

version_added: 0.4.0

description:
  - Set the encryption mode of the pod traffic of a PidginHost Kubernetes cluster.
  - Nothing changes when the cluster already has O(mode) and no change is running, or when a running change already
    targets O(mode).
  - The API refuses a change while another cluster operation runs, while the encryption state is unknown, and
    without O(acknowledge_workload_restart=true). The module fails with the reason the API gives.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_encryption_create).

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
  mode:
    description:
      - Encryption mode. V(none) turns encryption off.
    type: str
    choices: [none, wireguard]
    required: true
  acknowledge_workload_restart:
    description:
      - Accept that the workloads must be restarted after the change.
      - Passed to the API as is. The API refuses every change without it.
    type: bool
    default: false
  wait:
    description:
      - Wait until the change is done and verified, and fail if it fails.
      - Also wait for a change that is already running before comparing the mode.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Encrypt pod traffic with WireGuard
  pidginhost.cloud.kubernetes_cluster_encryption:
    cluster_name: prod
    mode: wireguard
    acknowledge_workload_restart: true
"""

RETURN = r"""
encryption:
  description:
    - Encryption state of the cluster.
    - C(status) is one of C(disabled), C(enabling), C(enabled_restart_required), C(enabled), C(disabling) or
      C(unknown). C(enabled_restart_required) means workloads started before the change still need a restart.
  returned: success
  type: dict
  sample:
    mode: wireguard
    status: enabled
    reason: ""
    error: ""
    restart_required: false
    stale_pod_count: 0
    operation:
      id: 4
      kind: toggle
      status: succeeded
      requested_mode: wireguard
      previous_mode: none
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec

SETTLED = ("disabled", "enabled", "enabled_restart_required")


def running(state):
    return (state.get("operation") or {}).get("status") in ("pending", "running")


def wait_quiet(api, module, path, changed):
    # The API creates the operation before it answers, so a fresh change always shows as running here.
    state = api.wait_for(lambda: api.get(path), lambda s: not running(s))
    if state is None:
        module.fail_json(changed=changed, msg="The encryption change did not finish in time.")
    return state


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            mode=dict(type="str", choices=["none", "wireguard"], required=True),
            acknowledge_workload_restart=dict(type="bool", default=False),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        mutually_exclusive=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    path = "%s%s/encryption/" % (CLUSTERS, cluster["id"])

    state = api.get(path)
    if params["wait"] and not module.check_mode and running(state):
        state = wait_quiet(api, module, path, changed=False)
    if running(state):
        done = state["operation"]["requested_mode"] == params["mode"]
    else:
        done = state["mode"] == params["mode"] and state["status"] in SETTLED
    if done:
        module.exit_json(changed=False, encryption=state)
    if module.check_mode:
        module.exit_json(changed=True, encryption=state)

    body = {"mode": params["mode"], "acknowledge_workload_restart": params["acknowledge_workload_restart"]}
    answer = api.post(path, body, allow_status=(400, 403, 404, 409))
    if api.status >= 400:
        reason = answer.get("reason") or answer.get("code")
        module.fail_json(
            msg="Kubernetes cluster %s refused the encryption change%s: %s"
                % (cluster["id"], " (%s)" % reason if reason else "", answer.get("message")),
            status_code=api.status,
            response=answer,
        )
    if not params["wait"]:
        module.exit_json(changed=True, encryption=api.get(path))

    state = wait_quiet(api, module, path, changed=True)
    if state["mode"] != params["mode"] or state["status"] not in SETTLED:
        operation = state.get("operation") or {}
        module.fail_json(
            changed=True,
            msg="The encryption change on Kubernetes cluster %s failed (%s): %s" % (
                cluster["id"], state["reason"] or operation.get("reason") or state["status"],
                state["error"] or operation.get("message") or "no details"),
            encryption=state,
        )
    module.exit_json(changed=True, encryption=state)


if __name__ == "__main__":
    main()
