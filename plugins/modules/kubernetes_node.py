# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_node

short_description: Reboot or delete a Kubernetes worker node.

version_added: 0.4.0

description:
  - Reboot or delete one worker node of a PidginHost Kubernetes cluster resource pool.
  - The node is cordoned and drained first. Draining destroys data kept on the node itself, and the API refuses
    the operation unless O(local_data_loss_accepted=true).
  - A delete confirms the node hostname to the API on your behalf.
  - O(state=rebooted) always reboots the node and reports a change.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_resource_pools_nodes_reboot_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - V(rebooted) reboots the node. V(absent) deletes it, and does nothing when it is already gone.
    type: str
    choices: [rebooted, absent]
    required: true
  cluster_id:
    description:
      - ID of the Kubernetes cluster. Takes precedence over O(cluster_name).
    type: int
  cluster_name:
    description:
      - Name of the Kubernetes cluster. Used when O(cluster_id) is not set, so it must be unique in the account.
    type: str
  pool_id:
    description:
      - ID of the resource pool that holds the node. See M(pidginhost.cloud.kubernetes_resource_pool).
    type: int
    required: true
  node:
    description:
      - Node name or ID.
    type: str
    required: true
  local_data_loss_accepted:
    description:
      - Accept that draining the node destroys data kept on the node itself. Passed to the API.
    type: bool
    default: false
  wait:
    description:
      - Wait until the node operation succeeds. Fail when it fails, is aborted, is blocked or needs attention.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Reboot a worker
  pidginhost.cloud.kubernetes_node:
    cluster_name: prod
    pool_id: 3
    node: prod-w1
    state: rebooted
    local_data_loss_accepted: true

- name: Delete a worker
  pidginhost.cloud.kubernetes_node:
    cluster_name: prod
    pool_id: 3
    node: prod-w1
    state: absent
    local_data_loss_accepted: true
"""

RETURN = r"""
operation:
  description:
    - The node operation. With O(wait=true), its final state.
    - Empty when nothing was done or in check mode.
  returned: success
  type: dict
  sample:
    id: 9
    kind: reboot
    source: api
    target_hostname: prod-w1
    status: succeeded
    reason: ""
    message: ""
    local_data_loss_accepted: true
    allowed_actions: []
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec

# blocked is not final: it waits for a retry with overrides or a cancel, which this module does not send.
STOPPED = ("succeeded", "failed", "aborted", "needs_attention", "blocked")


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["rebooted", "absent"], required=True),
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            pool_id=dict(type="int", required=True),
            node=dict(type="str", required=True),
            local_data_loss_accepted=dict(type="bool", default=False),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    cluster_path = "%s%s/" % (CLUSTERS, api.require_cluster(params["cluster_id"], params["cluster_name"])["id"])
    nodes_path = "%sresource-pools/%s/nodes/" % (cluster_path, params["pool_id"])
    nodes = api.list(nodes_path)
    node = api.find_one(nodes, "nodes", name=params["node"])
    if not node and params["node"].isdigit():
        node = api.find_one(nodes, "nodes", id=int(params["node"]))

    if not node:
        if params["state"] == "absent":
            module.exit_json(changed=False, operation={})
        module.fail_json(msg="Node %s not found in resource pool %s." % (params["node"], params["pool_id"]))
    if module.check_mode:
        module.exit_json(changed=True, operation={})

    ack = {"local_data_loss_accepted": params["local_data_loss_accepted"]}
    node_path = "%s%s/" % (nodes_path, node["id"])
    if params["state"] == "absent":
        operation = api.delete(node_path, body=dict(ack, confirm_hostname=node["name"]))
    else:
        operation = api.post(node_path + "reboot/", ack)

    if params["wait"]:
        op_path = "%snode-operations/%s/" % (cluster_path, operation["id"])
        done = api.wait_for(lambda: api.get(op_path), lambda o: o["status"] in STOPPED)
        if not done:
            module.fail_json(changed=True, msg="Node operation %s did not finish in time." % operation["id"],
                             operation=operation)
        if done["status"] != "succeeded":
            msg = " ".join(part for part in (
                "Node %s %s is %s." % (node["name"], done["kind"], done["status"]),
                done["message"],
                done["reason"] and "Reason: %s." % done["reason"],
                "Allowed actions: %s." % (", ".join(done["allowed_actions"]) or "none"),
            ) if part)
            module.fail_json(changed=True, msg=msg, operation=done)
        operation = done
    module.exit_json(changed=True, operation=operation)


if __name__ == "__main__":
    main()
