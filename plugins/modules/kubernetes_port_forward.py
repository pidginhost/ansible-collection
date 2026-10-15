# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_port_forward

short_description: Manage port forwards of a Kubernetes cluster load balancer.

version_added: 0.4.0

description:
  - Create, update or delete a port forward from the cluster load balancer to an internal address.
  - The forward is identified by O(port) and O(protocol). An existing forward is updated in place for
    O(internal_ip).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_port_forwards_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the forward should exist.
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
  port:
    description:
      - Port forwarded on the load balancer.
    type: int
    required: true
  protocol:
    description:
      - Protocol forwarded.
    type: str
    choices: [tcp, udp]
    required: true
  internal_ip:
    description:
      - IPv4 address the traffic is forwarded to. Required to create a forward.
    type: str
"""

EXAMPLES = r"""
- name: Forward TCP port 8080 to an internal address
  pidginhost.cloud.kubernetes_port_forward:
    cluster_name: prod
    port: 8080
    protocol: tcp
    internal_ip: 192.0.2.20

- name: Remove the forward
  pidginhost.cloud.kubernetes_port_forward:
    cluster_name: prod
    port: 8080
    protocol: tcp
    state: absent
"""

RETURN = r"""
port_forward:
  description:
    - Forward details. After deletion, the details before deletion. Empty when the forward does not exist.
  returned: success
  type: dict
  sample:
    id: 2
    internal_ip: 192.0.2.20
    port: 8080
    protocol: tcp
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            port=dict(type="int", required=True),
            protocol=dict(type="str", choices=["tcp", "udp"], required=True),
            internal_ip=dict(type="str"),
        ),
        required_one_of=[("cluster_id", "cluster_name")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    path = "%s%s/port-forwards/" % (CLUSTERS, cluster["id"])
    forward = api.find_one(api.list(path), "port forwards", port=params["port"], protocol=params["protocol"])

    if params["state"] == "absent":
        if not forward:
            module.exit_json(changed=False, port_forward={})
        if not module.check_mode:
            api.delete("%s%s/" % (path, forward["id"]))
        module.exit_json(changed=True, port_forward=forward)

    if not forward:
        if not params["internal_ip"]:
            module.fail_json(msg="Creating a port forward requires: internal_ip")
        if module.check_mode:
            module.exit_json(changed=True, port_forward={})
        body = dict((k, params[k]) for k in ("port", "protocol", "internal_ip"))
        module.exit_json(changed=True, port_forward=api.post(path, body))

    if params["internal_ip"] is None or params["internal_ip"] == forward["internal_ip"]:
        module.exit_json(changed=False, port_forward=forward)
    if module.check_mode:
        module.exit_json(changed=True, port_forward=forward)
    module.exit_json(changed=True, port_forward=api.patch(
        "%s%s/" % (path, forward["id"]), {"internal_ip": params["internal_ip"]}))


if __name__ == "__main__":
    main()
