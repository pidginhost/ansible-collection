# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: public_interface_info

short_description: Get the public interface of a cloud server.

version_added: 0.2.0

description:
  - Return the public network interface of a PidginHost cloud server, with its addresses and firewall settings.
  - The server is identified by O(server_id) or by its unique O(server_hostname).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_public_interface_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info

options:
  server_id:
    description:
      - ID of the server. Takes precedence over O(server_hostname).
    type: int
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
"""

EXAMPLES = r"""
- name: Get the public interface of a server
  pidginhost.cloud.public_interface_info:
    server_id: 12345
  register: result

- name: Get it by hostname
  pidginhost.cloud.public_interface_info:
    server_hostname: web1.example.com
  register: result
"""

RETURN = r"""
interfaces:
  description:
    - Public interface of the server. Empty when the server has no public IP address.
  returned: success
  type: dict
  sample:
    interface: net0
    ipv4: 192.0.2.10
    ipv6: 2001:db8::10
    fw_rules_set: web
    fw_policy_in: DROP
    fw_policy_out: ACCEPT
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=info_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    server = api.require_server(module.params["server_id"], module.params["server_hostname"])
    # The API answers 404 when the server has no public IP address.
    interface = api.get("%s%s/public-interface/" % (SERVERS, server["id"]), allow_404=True)
    module.exit_json(changed=False, interfaces=interface or {})


if __name__ == "__main__":
    main()
