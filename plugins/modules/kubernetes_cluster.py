# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_cluster

short_description: Create, update or delete Kubernetes clusters.

version_added: 0.4.0

description:
  - Create, update or delete PidginHost managed Kubernetes clusters.
  - The cluster is identified by O(cluster_id) or by its unique O(name).
  - An existing cluster is updated in place for O(features) and O(protected), and for O(name) when O(cluster_id) is
    set. Other options only apply when the cluster is created.
  - Use M(pidginhost.cloud.kubernetes_cluster_upgrade) to upgrade a cluster and
    M(pidginhost.cloud.kubernetes_resource_pool) to manage its worker pools.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the cluster should exist.
    type: str
    choices: [present, absent]
    default: present
  cluster_id:
    description:
      - ID of an existing cluster.
    type: int
  name:
    description:
      - Cluster name. Used to find the cluster when O(cluster_id) is not set, so it must be unique in the account.
      - With O(cluster_id), the cluster is renamed to this name.
    type: str
  cluster_type:
    description:
      - Cluster type. Required to create a cluster. See M(pidginhost.cloud.kubernetes_cluster_types_info).
      - New V(prod) clusters are protected from deletion unless O(protected=false).
    type: str
    choices: [dev, prod, beta]
  resource_pool_package:
    description:
      - Package ID or slug of the first worker pool. Required to create a cluster.
      - Must be one of the worker node packages of O(cluster_type).
    type: str
  resource_pool_size:
    description:
      - Number of worker nodes in the first pool. The cluster type minimum when not set.
    type: int
  kube_version:
    description:
      - Kubernetes version, for example V(1.35.7). The latest offered version when not set.
    type: str
  enable_gateway_api:
    description:
      - Enable the Gateway API on creation. The API enables it when not set.
    type: bool
  dual_stack:
    description:
      - Enable IPv6 dual stack for pods, services and the cluster private network.
      - The API ignores it when the platform does not offer dual stack. Cannot be changed after creation.
    type: bool
  generation:
    description:
      - Hardware generation slug. See M(pidginhost.cloud.generations_info).
    type: str
  features:
    description:
      - Optional cluster features, compared as a set.
      - Known values are V(cert-manager), V(ceph-csi), V(metrics-server), V(cloudnative-pg), V(mariadb-operator),
        V(mongodb-operator) and V(lb-envoy-metrics).
      - Features install in the background after the change. The API refuses a change while C(features_ready) is
        false; with O(wait=true) the module waits for it first.
    type: list
    elements: str
  protected:
    description:
      - Protect the cluster from deletion.
      - Setting it on a new cluster requires O(wait=true).
      - With O(state=absent), V(false) turns protection off before deleting the cluster.
    type: bool
  wait:
    description:
      - Wait until a new cluster is active, or until a deleted cluster is gone.
      - Also wait for C(features_ready) before changing O(features).
      - Provisioning a cluster can take longer than the default O(timeout).
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Create a cluster with three workers
  pidginhost.cloud.kubernetes_cluster:
    name: prod
    cluster_type: prod
    resource_pool_package: k8s-w2
    resource_pool_size: 3
    features:
      - cert-manager
      - metrics-server
    timeout: 1800
  register: cluster

- name: Delete the cluster, turning protection off first
  pidginhost.cloud.kubernetes_cluster:
    name: prod
    state: absent
    protected: false
"""

RETURN = r"""
cluster:
  description:
    - Cluster details. After deletion, the details before deletion. Empty when the cluster does not exist.
    - With O(wait=false), only the ID of a newly created cluster.
  returned: success
  type: dict
  sample:
    id: 7
    name: prod
    status: active
    cluster_type: prod
    kube_version: 1.35.7
    features:
      - cert-manager
    features_ready: true
    protected: true
    ipv4_address: 192.0.2.20
    ipv6_address: 2001:db8::20
    talos_upgrade_available: false
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, drop_none, pidginhost_argument_spec

CREATE_FIELDS = (
    "name", "cluster_type", "resource_pool_package", "resource_pool_size", "kube_version", "features",
    "enable_gateway_api", "dual_stack", "generation",
)
# The API hides cancelled and terminated clusters but keeps listing these until the deletion completes.
DELETING = ("cancelling", "terminating")


def cluster_path(cluster_id):
    return "%s%s/" % (CLUSTERS, cluster_id)


def create(api, module):
    params = module.params
    missing = [name for name in ("cluster_type", "resource_pool_package") if not params[name]]
    if missing:
        module.fail_json(msg="Creating a Kubernetes cluster requires: %s" % ", ".join(missing))
    if params["protected"] is not None and not params["wait"]:
        module.fail_json(msg="Setting protected on a new cluster requires wait=true.")
    if module.check_mode:
        module.exit_json(changed=True, cluster={})

    cluster_id = api.post(CLUSTERS, drop_none(dict((k, params[k]) for k in CREATE_FIELDS)))["id"]
    if not params["wait"]:
        module.exit_json(changed=True, cluster={"id": cluster_id})

    # New clusters answer 404 while pending, then move through provisioning to active or failed.
    path = cluster_path(cluster_id)
    cluster = api.wait_for(lambda: api.get(path, allow_404=True),
                           lambda c: c is not None and c["status"] in ("active", "failed"))
    if not cluster or cluster["status"] != "active":
        module.fail_json(
            changed=True,
            msg="Kubernetes cluster %s %s." % (
                cluster_id, "failed to provision" if cluster else "did not become active in time"),
            cluster=cluster or {"id": cluster_id},
        )
    # Protection is not a creation field, and prod clusters start protected.
    if params["protected"] is not None and params["protected"] != cluster["protected"]:
        cluster = api.patch(path, {"protected": params["protected"]})
    module.exit_json(changed=True, cluster=cluster)


def update(api, module, cluster):
    params = module.params
    if cluster["status"] in DELETING:
        module.fail_json(msg="Kubernetes cluster %s is being deleted." % cluster["id"], cluster=cluster)
    changes = {}
    if params["features"] is not None and set(params["features"]) != set(cluster["features"] or []):
        changes["features"] = params["features"]
    if params["protected"] is not None and params["protected"] != cluster["protected"]:
        changes["protected"] = params["protected"]
    if params["cluster_id"] and params["name"] is not None and params["name"] != cluster["name"]:
        changes["name"] = params["name"]
    if not changes:
        module.exit_json(changed=False, cluster=cluster)
    if module.check_mode:
        module.exit_json(changed=True, cluster=cluster)

    path = cluster_path(cluster["id"])
    if "features" in changes and not cluster["features_ready"] and params["wait"]:
        if not api.wait_for(lambda: api.get(path), lambda c: c["features_ready"]):
            module.fail_json(msg="Kubernetes cluster %s features were not ready in time." % cluster["id"],
                             cluster=cluster)
    module.exit_json(changed=True, cluster=api.patch(path, changes))


def delete(api, module, cluster):
    changed = cluster["status"] not in DELETING
    if changed and cluster["protected"] and module.params["protected"] is not False:
        module.fail_json(msg="Kubernetes cluster %s is protected from deletion. Set protected=false to delete it."
                         % cluster["id"], cluster=cluster)
    if module.check_mode:
        module.exit_json(changed=changed, cluster=cluster)

    path = cluster_path(cluster["id"])
    if changed:
        if cluster["protected"]:
            api.patch(path, {"protected": False})
        api.delete(path)
    if module.params["wait"]:
        status = api.wait_for(lambda: (api.get(path, allow_404=True) or {"status": "gone"})["status"],
                              lambda s: s not in DELETING)
        if status not in ("gone", "cancelled", "terminated"):
            reason = "was not deleted in time" if status is None else "failed to delete"
            module.fail_json(changed=changed, msg="Kubernetes cluster %s %s." % (cluster["id"], reason),
                             cluster=cluster)
    module.exit_json(changed=changed, cluster=cluster)


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            cluster_id=dict(type="int"),
            name=dict(type="str"),
            cluster_type=dict(type="str", choices=["dev", "prod", "beta"]),
            resource_pool_package=dict(type="str"),
            resource_pool_size=dict(type="int"),
            kube_version=dict(type="str"),
            enable_gateway_api=dict(type="bool"),
            dual_stack=dict(type="bool"),
            generation=dict(type="str"),
            features=dict(type="list", elements="str"),
            protected=dict(type="bool"),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("cluster_id", "name")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    cluster = api.find_cluster(params["cluster_id"], params["name"])

    if params["state"] == "absent":
        if not cluster:
            module.exit_json(changed=False, cluster={})
        delete(api, module, cluster)
    elif cluster:
        update(api, module, cluster)
    elif params["cluster_id"]:
        module.fail_json(msg="Kubernetes cluster %s not found." % params["cluster_id"])
    else:
        create(api, module)


if __name__ == "__main__":
    main()
