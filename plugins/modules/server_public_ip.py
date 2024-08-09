# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pidginhost.cloud.server_public_ip

short_description: Get specific server ip.

version_added: 0.2.0

description:
  - Get specific server id.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

options:
  server_hostname:
    description:
      - The hostname of the Server to act on.
      - If provided, must be unique.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Get specific server ip
  pidginhost.cloud.server_public_ip:
    token: "{{ token }}"
    state: present
    server_hostname: "{{ server_hostname }}"
"""

RETURN = r"""
server:
  description:
    - Get specific server ip.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    server: 176.124.106.79

error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code

msg:
  description: Action information.
  returned: always
  type: str
  sample:
    - No Server named with hostname HOSTNAME
    - Multiple Servers (11) found, with hostname: (HOSTNAME)
    - Find Server id: 232 with ip address: IP_ADDRESS
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
