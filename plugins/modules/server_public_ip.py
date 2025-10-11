# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_public_ip

short_description: Retrieve the public IPv4 address for a server.

version_added: 0.2.0

description:
  - Retrieve the public IPv4 address for a server identified by hostname.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  server_hostname:
    description:
      - Hostname of the server.
      - Must resolve to a unique server.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve server public IPv4 address
  pidginhost.cloud.server_public_ip:
    state: present
    server_hostname: hostname
"""

import time
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class ServerPublicIP(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.hostname = module.params.get('server_hostname')
        if self.state == "present":
            self.present()

    def find_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named with hostname {self.hostname}",
                server=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                server=[],
            )
        return servers[0]

    def present(self):
        time.sleep(3)
        server = self.find_server_by_hostname()
        self.module.exit_json(
            changed=False,
            msg=f"Find Server id: {server['id']} with ip address: {server['networks']['public']['ipv4']}",
            server=server['networks']['public']['ipv4'],
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        server_hostname=dict(type="str", required=True),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    ServerPublicIP(module)


if __name__ == '__main__':
    main()
