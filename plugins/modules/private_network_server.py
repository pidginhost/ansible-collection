# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: private_network_server

short_description: Add servers to private networks or remove them.

version_added: 0.4.0

description:
  - Add a server to a private network, or remove it.
  - The server must be active to be added.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_private_networks_add_server_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the server should be on the network.
    type: str
    choices: [present, absent]
    default: present
  network:
    description:
      - ID or CIDR address of the private network.
    type: str
    required: true
  server_id:
    description:
      - ID of the server. Takes precedence over O(server_hostname).
    type: int
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
  address:
    description:
      - Private IPv4 address of the server in the network. Assigned automatically when not set.
      - A server already on the network with another address is removed and added again with this one.
    type: str
"""

EXAMPLES = r"""
- name: Add a server to a private network
  pidginhost.cloud.private_network_server:
    network: 198.51.100.0/24
    server_hostname: web1.example.com
    address: 198.51.100.10

- name: Remove a server from a private network
  pidginhost.cloud.private_network_server:
    state: absent
    network: "5"
    server_id: 12345
"""

RETURN = r"""
server:
  description:
    - The server membership in the network. After removal, the membership before removal.
    - Empty when the server is not on the network, or when it is added in check mode.
  returned: success
  type: dict
  sample:
    interface: eth1
    address: 198.51.100.10
    network: 198.51.100.0/24
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, pidginhost_argument_spec

NETWORKS = "/api/cloud/private-networks/"


def find_network(api, network):
    if network.isdigit():
        return api.get("%s%s/" % (NETWORKS, network), allow_404=True)
    return api.find_one(api.list(NETWORKS), "private networks", address=network)


def membership(server, network):
    return next((m for m in server["networks"]["private"] if m["network"] == network["address"]), {})


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            network=dict(type="str", required=True),
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            address=dict(type="str"),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    present = params["state"] == "present"

    network = find_network(api, params["network"])
    if not network:
        if present:
            module.fail_json(msg="Private network %s not found." % params["network"])
        module.exit_json(changed=False, server={})
    find = api.require_server if present else api.find_server
    server = find(params["server_id"], params["server_hostname"])
    member = membership(server, network) if server else {}
    path = "%s%s/" % (NETWORKS, network["id"])

    if present and member and params["address"] in (None, member["address"]):
        module.exit_json(changed=False, server=member)
    if not present and not member:
        module.exit_json(changed=False, server={})
    if module.check_mode:
        module.exit_json(changed=True, server=member)

    if member:
        # The private address is unique in the network, unlike a hostname.
        api.post(path + "remove-server/", {"server": member["address"]})
    if not present:
        module.exit_json(changed=True, server=member)
    api.post(path + "add-server/", drop_none({"server": str(server["id"]), "address": params["address"]}))
    module.exit_json(changed=True, server=membership(api.get("%s%s/" % (SERVERS, server["id"])), network))


if __name__ == "__main__":
    main()
