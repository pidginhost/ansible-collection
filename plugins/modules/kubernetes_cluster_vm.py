# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kubernetes_cluster_vm

short_description: Connect cloud servers to a Kubernetes cluster private network.

version_added: 0.4.0

description:
  - Connect a PidginHost cloud server to the private network of a Kubernetes cluster, or disconnect it.
  - Connecting or disconnecting reboots the server.
  - Only active servers can be connected, and only to a cluster with cloud VM access enabled. The API offers no
    way to read that setting, only to toggle it, so this module does not manage it. Enable it in the control
    panel first.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/kubernetes/kubernetes_clusters_connect_vm_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the server should be connected to the cluster private network.
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
  server_id:
    description:
      - ID of the cloud server. Takes precedence over O(server_hostname).
    type: int
  server_hostname:
    description:
      - Hostname of the cloud server. Used when O(server_id) is not set, so it must be unique in the account.
    type: str
  wait:
    description:
      - Wait until the cluster lists the server as connected, or no longer lists it after a disconnect.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Connect a database server to the cluster network
  pidginhost.cloud.kubernetes_cluster_vm:
    cluster_name: prod
    server_hostname: db1.example.com

- name: Disconnect it
  pidginhost.cloud.kubernetes_cluster_vm:
    cluster_name: prod
    server_hostname: db1.example.com
    state: absent
"""

RETURN = r"""
vm:
  description:
    - The connected server with its address on the cluster network. After a disconnect, the entry before it.
    - Without the address when the connection was not awaited or in check mode.
    - Empty when the server is not connected and O(state=absent).
  returned: success
  type: dict
  sample:
    id: 42
    hostname: db1.example.com
    ip: 192.0.2.100
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import CLUSTERS, PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            cluster_id=dict(type="int"),
            cluster_name=dict(type="str"),
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("cluster_id", "cluster_name"), ("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    cluster = api.require_cluster(params["cluster_id"], params["cluster_name"])
    path = "%s%s/" % (CLUSTERS, cluster["id"])
    match = dict(id=params["server_id"]) if params["server_id"] else dict(hostname=params["server_hostname"])

    def connected():
        return api.find_one(api.get(path + "connected-vms/")["vms"], "connected servers", **match)

    vm = connected()
    if params["state"] == "absent":
        if not vm:
            module.exit_json(changed=False, vm={})
        if module.check_mode:
            module.exit_json(changed=True, vm=vm)
        api.post(path + "disconnect-vm/", {"server": vm["id"]})
        if params["wait"] and not api.wait_for(lambda: connected() is None, bool):
            module.fail_json(changed=True, msg="Server %s was not disconnected in time." % vm["hostname"], vm=vm)
        module.exit_json(changed=True, vm=vm)

    if vm:
        module.exit_json(changed=False, vm=vm)
    # The API lists a server as eligible only when cloud VM access is on and the server is active.
    server = api.find_one(api.get(path + "eligible-vms/")["vms"], "servers", **match)
    if not server:
        module.fail_json(
            msg="Server %s cannot be connected to cluster %s. Enable cloud VM access for the cluster in the "
                "control panel, and make sure the server exists and is active."
                % (params["server_id"] or params["server_hostname"], cluster["name"]))
    if module.check_mode:
        module.exit_json(changed=True, vm=server)
    api.post(path + "connect-vm/", {"server": server["id"]})
    if params["wait"]:
        vm = api.wait_for(connected, lambda found: found is not None)
        if not vm:
            module.fail_json(changed=True, msg="Server %s was not connected in time." % server["hostname"],
                             vm=server)
    module.exit_json(changed=True, vm=vm or server)


if __name__ == "__main__":
    main()
