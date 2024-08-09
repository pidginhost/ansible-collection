# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: servers_info

short_description: List all Servers info.

version_added: 0.2.0

description:
  - List all Servers info.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_list).

author:
  - Popescu Andrei Cristian (@shbpty)

"""

EXAMPLES = r"""
- name: Print Servers info
  pidginhost.cloud.servers_info:
    token: "{{ token }}"
    state: present
"""

RETURN = r"""
servers:
  changed: false
  failed: false
  msg: "All Servers info."
  servers:
    cpus: 2
    disk_size: 64
    hostname: "hhtest22332.com"
    id: 707
    image: "ubuntu22"
    memory: 4
    networks:
      private: []
      public:
        interface: "eth0"
        ipv4: "176.124.106.104"
        ipv6: "2001:67c:744:1::22"
    package: "cloudv-3"
    project: "z5"
    status: "active"

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
    - All Servers info..
    - No Server info.
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class ServersInfo(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        server_data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        self.module.exit_json(
            changed=False,
            msg=f"All Servers info.",
            servers=server_data.get("results")[0],
        )
        self.module.exit_json(changed=False, msg="No Server info.", servers=[])


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    ServersInfo(module)


if __name__ == '__main__':
    main()
