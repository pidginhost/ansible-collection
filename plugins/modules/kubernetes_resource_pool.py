# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_resource_pool

short_description: Create, resize or delete Kubernetes worker pools.

version_added: 0.4.0

description:
  - Create, resize or delete a resource pool (a group of worker nodes) of a PidginHost Kubernetes cluster.
  - The pool is identified by O(pool_id), or by O(package) and O(generation) when they match exactly one pool.
    A cluster holds at most one pool per package and generation.
  - Removing workers (a smaller O(size) or O(state=absent) on a pool with nodes) drains them and destroys data
    kept on the nodes. The API refuses it unless O(local_data_loss_accepted=true).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_resource_pools_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the pool should exist.
    type: str
    choices: [present, absent]
    default: present
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
      - ID of an existing pool. When set, O(package) and O(generation) are ignored.
    type: int
  package:
    description:
      - Worker node package slug. Identifies the pool when O(pool_id) is not set, and is the package of a new pool.
    type: str
  generation:
    description:
      - Hardware generation slug. Narrows the match on O(package), and is the generation of a new pool.
      - New pools use the cluster generation when not set.
    type: str
  size:
    description:
      - Number of worker nodes. Required to create a pool. Not changed when not set.
    type: int
  local_data_loss_accepted:
    description:
      - Accept that removing workers destroys data kept on the nodes themselves.
      - Passed to the API when the pool is shrunk or deleted. The API refuses to remove workers without it.
    type: bool
    default: false
  wait:
    description:
      - Wait until the cluster has finished the change.
      - For a shrink or the deletion of a pool with nodes, wait for the pool removal journal to succeed,
        and fail if it fails or needs attention.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Add a pool of two workers
  pidginhost.cloud.kubernetes_resource_pool:
    cluster_name: prod
    package: k8s-w2
    size: 2

- name: Shrink the pool to one worker
  pidginhost.cloud.kubernetes_resource_pool:
    cluster_name: prod
    package: k8s-w2
    size: 1
    local_data_loss_accepted: true

- name: Delete the pool
  pidginhost.cloud.kubernetes_resource_pool:
    cluster_name: prod
    pool_id: 3
    state: absent
    local_data_loss_accepted: true
"""

RETURN = r"""
resource_pool:
  description:
    - Pool details. After deletion, the details before deletion. Empty when the pool does not exist.
  returned: success
  type: dict
  sample:
    id: 3
    package: k8s-w2
    generation: gen3
    size: 2
    nodes:
      - id: 11
        name: prod-w1
        ip: 192.0.2.11
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, drop_none, pidginhost_argument_spec

# A journal stops at one of these. needs_attention is parked for support, not finished, but nothing
# the module can do will move it on.
JOURNAL_DONE = ("succeeded", "failed", "needs_attention")


def find_pool(api, module, pools_path):
    params = module.params
    if params["pool_id"]:
        found = api.get("%s%s/" % (pools_path, params["pool_id"]), allow_404=True)
        if not found and params["state"] == "present":
            module.fail_json(msg="Resource pool %s not found." % params["pool_id"])
        return found
    match = drop_none(dict(package=params["package"], generation=params["generation"]))
    return api.find_one(api.list(pools_path), "resource pools", **match)


def last_journal_id(api, journals_path):
    # The list is newest first.
    items = api.get(journals_path).get("results") or [{"id": 0}]
    return items[0]["id"]


def wait_journal(api, module, journals_path, after, pool):
    """Wait for the removal journal created after journal id `after`."""
    def newest():
        return next((j for j in api.get(journals_path).get("results") or [] if j["id"] > after), None)

    journal = api.wait_for(newest, lambda j: j is not None and j["status"] in JOURNAL_DONE)
    if not journal or journal["status"] != "succeeded":
        msg = "Removal of workers from pool %s did not finish in time." % pool["id"]
        if journal:
            msg = "Removal of workers from pool %s is %s: %s" % (pool["id"], journal["status"], journal["message"])
        module.fail_json(changed=True, msg=msg, journal=journal, resource_pool=pool)


def wait_cluster(api, module, cluster_path, pool):
    cluster = api.wait_for(lambda: api.get(cluster_path), lambda c: c["status"] in ("active", "failed"))
    if not cluster or cluster["status"] != "active":
        reason = "failed" if cluster else "did not finish in time"
        module.fail_json(changed=True, msg="The pool change on the cluster %s." % reason, resource_pool=pool)


def changed_pool(api, module, pools_path, pool_id):
    # A failed pool change still returns the cluster to active, so the node count is what tells.
    pool = api.get("%s%s/" % (pools_path, pool_id), allow_404=True) or {}
    if module.params["wait"] and pool.get("size") != module.params["size"]:
        module.fail_json(changed=True, resource_pool=pool, msg="Resource pool %s has %s nodes instead of %s." % (
            pool_id, pool.get("size", 0), module.params["size"]))
    return pool


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            pool_id=dict(type="int"),
            package=dict(type="str"),
            generation=dict(type="str"),
            size=dict(type="int"),
            local_data_loss_accepted=dict(type="bool", default=False),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("cluster_id", "cluster_name"), ("pool_id", "package")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    cluster_path = "%s%s/" % (CLUSTERS, api.require_cluster(params["cluster_id"], params["cluster_name"])["id"])
    pools_path = cluster_path + "resource-pools/"
    journals_path = cluster_path + "pool-removal-journals/"
    pool = find_pool(api, module, pools_path)
    ack = {"local_data_loss_accepted": params["local_data_loss_accepted"]}

    if params["state"] == "absent":
        if not pool:
            module.exit_json(changed=False, resource_pool={})
        if module.check_mode:
            module.exit_json(changed=True, resource_pool=pool)
        # A pool with nodes is removed through a journal; an empty one goes at once.
        after = last_journal_id(api, journals_path) if pool["nodes"] else None
        api.delete("%s%s/" % (pools_path, pool["id"]), body=ack)
        if params["wait"]:
            if after is None:
                wait_cluster(api, module, cluster_path, pool)
            else:
                wait_journal(api, module, journals_path, after, pool)
        module.exit_json(changed=True, resource_pool=pool)

    if not pool:
        if params["size"] is None:
            module.fail_json(msg="Creating a resource pool requires: size")
        if module.check_mode:
            module.exit_json(changed=True, resource_pool={})
        pool = api.post(pools_path, drop_none(dict(
            resource_pool_package=params["package"], resource_pool_size=params["size"],
            generation=params["generation"])))
        if params["wait"]:
            wait_cluster(api, module, cluster_path, pool)
        module.exit_json(changed=True, resource_pool=changed_pool(api, module, pools_path, pool["id"]))

    if params["size"] is None or params["size"] == pool["size"]:
        module.exit_json(changed=False, resource_pool=pool)
    if module.check_mode:
        module.exit_json(changed=True, resource_pool=pool)
    shrink = params["size"] < pool["size"]
    after = last_journal_id(api, journals_path) if shrink else None
    api.patch("%s%s/" % (pools_path, pool["id"]), dict(ack, new_size=params["size"]))
    if params["wait"]:
        if shrink:
            wait_journal(api, module, journals_path, after, pool)
        else:
            wait_cluster(api, module, cluster_path, pool)
    module.exit_json(changed=True, resource_pool=changed_pool(api, module, pools_path, pool["id"]))


if __name__ == "__main__":
    main()
