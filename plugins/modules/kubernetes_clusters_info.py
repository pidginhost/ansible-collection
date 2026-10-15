# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_clusters_info

short_description: List Kubernetes clusters.

version_added: 0.4.0

description:
  - List every PidginHost Kubernetes cluster in the account.
  - With O(cluster_id) or O(cluster_name), return only that cluster, with the extra data selected by O(include).
  - Use M(pidginhost.cloud.kubernetes_kubeconfig) to read the kubeconfig.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  cluster_id:
    description:
      - ID of the cluster to return.
    type: int
  cluster_name:
    description:
      - Name of the cluster to return. Must be unique in the account.
    type: str
  include:
    description:
      - Extra data to add to the selected cluster, each under a key of the same name.
      - V(resource_pools) lists the worker pools and their nodes.
      - V(http_routes), V(tcp_routes) and V(udp_routes) list the Gateway API routes.
      - V(port_forwards) and V(lb_firewall) list the load balancer port forwards and firewall rules.
      - V(connected_vms) lists the cloud servers connected to the cluster private network.
        V(eligible_vms) lists the servers that can be connected.
      - V(encryption) is the WireGuard encryption state.
      - V(node_operations) and V(pool_removal_journals) list node reboots and deletions, pool downsizes and pool
        deletions.
      - Requires O(cluster_id) or O(cluster_name).
    type: list
    elements: str
    choices:
      - resource_pools
      - http_routes
      - tcp_routes
      - udp_routes
      - port_forwards
      - lb_firewall
      - connected_vms
      - eligible_vms
      - encryption
      - node_operations
      - pool_removal_journals
"""

EXAMPLES = r"""
- name: List every cluster
  pidginhost.cloud.kubernetes_clusters_info:
  register: result

- name: Get one cluster with its worker pools and encryption state
  pidginhost.cloud.kubernetes_clusters_info:
    cluster_name: prod
    include:
      - resource_pools
      - encryption
  register: result
"""

RETURN = r"""
clusters:
  description:
    - Every cluster in the account, or a one item list with the selected cluster.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 7
      name: prod
      status: active
      cluster_type: prod
      kube_version: 1.35.7
      features:
        - cert-manager
      features_ready: true
      protected: true
      ipv4_address: 192.0.2.20
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec

INCLUDES = [
    "resource_pools", "http_routes", "tcp_routes", "udp_routes", "port_forwards", "lb_firewall", "connected_vms",
    "eligible_vms", "encryption", "node_operations", "pool_removal_journals",
]


def fetch(api, path, name):
    # http_routes is served at httproutes/, resource_pools at resource-pools/.
    path += "%s/" % name.replace("_routes", "routes").replace("_", "-")
    if name == "encryption":
        return api.get(path)
    if name in ("connected_vms", "eligible_vms"):
        return api.get(path)["vms"]
    return api.list(path)


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            include=dict(type="list", elements="str", choices=INCLUDES),
        ),
        mutually_exclusive=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    params = module.params
    selected = params["cluster_id"] or params["cluster_name"]
    if params["include"] and not selected:
        module.fail_json(msg="include requires cluster_id or cluster_name.")
    api = PidginHostAPI(module)
    if not selected:
        module.exit_json(changed=False, clusters=api.list(CLUSTERS))

    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    path = "%s%s/" % (CLUSTERS, cluster["id"])
    for name in params["include"] or []:
        cluster[name] = fetch(api, path, name)
    module.exit_json(changed=False, clusters=[cluster])


if __name__ == "__main__":
    main()
