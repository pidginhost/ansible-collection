# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: private_network

short_description: Manage private networks.

version_added: 0.4.0

description:
  - Create, update or delete private networks.
  - The network is identified by its O(address).
  - Use M(pidginhost.cloud.private_network_server) to add servers to a network.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_private_networks_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the network should exist.
      - Deleting a network also removes every server from it.
    type: str
    choices: [present, absent]
    default: present
  address:
    description:
      - Network address in CIDR format. Must match the address the API reports, for example V(198.51.100.0/24).
    type: str
    required: true
  gateway:
    description:
      - Gateway address inside the network.
    type: str
"""

EXAMPLES = r"""
- name: Create a private network
  pidginhost.cloud.private_network:
    address: 198.51.100.0/24
    gateway: 198.51.100.1

- name: Delete a private network
  pidginhost.cloud.private_network:
    state: absent
    address: 198.51.100.0/24
"""

RETURN = r"""
private_network:
  description:
    - The private network. After deletion, the details before deletion.
    - Empty when it did not exist, or when it is created in check mode.
  returned: success
  type: dict
  sample:
    id: 5
    slug: 198.51.100.0/24
    address: 198.51.100.0/24
    gateway: 198.51.100.1
    provisioned: true
    servers: []
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, pidginhost_argument_spec

NETWORKS = "/api/cloud/private-networks/"


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            address=dict(type="str", required=True),
            gateway=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    network = api.find_one(api.list(NETWORKS), "private networks", address=params["address"])

    if params["state"] == "absent":
        if not network:
            module.exit_json(changed=False, private_network={})
        if not module.check_mode:
            api.delete("%s%s/" % (NETWORKS, network["id"]))
        module.exit_json(changed=True, private_network=network)

    if not network:
        if module.check_mode:
            module.exit_json(changed=True, private_network={})
        module.exit_json(changed=True, private_network=api.post(
            NETWORKS, drop_none({"address": params["address"], "gateway": params["gateway"]})))

    if params["gateway"] is None or params["gateway"] == network["gateway"]:
        module.exit_json(changed=False, private_network=network)
    if not module.check_mode:
        network = api.patch("%s%s/" % (NETWORKS, network["id"]), {"gateway": params["gateway"]})
    module.exit_json(changed=True, private_network=network)


if __name__ == "__main__":
    main()
