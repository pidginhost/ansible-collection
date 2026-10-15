# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_public_ip

short_description: Get the public IP addresses of a cloud server.

version_added: 0.2.0

description:
  - Return the public IPv4 and IPv6 addresses and the networks of a PidginHost cloud server.
  - The server is identified by O(server_id) or by its unique O(server_hostname).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_retrieve).

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
- name: Get the public IPv4 address of a server
  pidginhost.cloud.server_public_ip:
    server_hostname: web1.example.com
  register: result

- name: Show it
  ansible.builtin.debug:
    msg: "{{ result.ipv4 }}"
"""

RETURN = r"""
server:
  description:
    - Public IPv4 address of the server. Same value as RV(ipv4), kept for earlier playbooks.
  returned: success
  type: str
  sample: 192.0.2.10
ipv4:
  description:
    - Public IPv4 address of the server. Null when the server has none.
  returned: success
  type: str
  sample: 192.0.2.10
ipv6:
  description:
    - Public IPv6 address of the server. Null when the server has none.
  returned: success
  type: str
  sample: 2001:db8::10
networks:
  description:
    - Public and private networks of the server.
  returned: success
  type: dict
  sample:
    public:
      interface: net0
      ipv4: 192.0.2.10
      ipv6: 2001:db8::10
      interfaces: []
    private:
      - interface: net1
        address: 198.51.100.2
        network: 198.51.100.0/24
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=info_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    server = PidginHostAPI(module).require_server(module.params["server_id"], module.params["server_hostname"])
    networks = server.get("networks") or {}
    public = networks.get("public") or {}
    module.exit_json(
        changed=False,
        server=public.get("ipv4"),
        ipv4=public.get("ipv4"),
        ipv6=public.get("ipv6"),
        networks=networks,
    )


if __name__ == "__main__":
    main()
