# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volumes_info

short_description: Get public interface for specific server.

version_added: 0.2.0

description:
  - Get public interface for specific server.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_public_interface_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

"""

EXAMPLES = r"""
- name: Print public interface
  pidginhost.cloud.public_interface_info:
    state: present
    server_id: 624
"""

RETURN = r"""
interfaces:
  description: 
    - Represents the information about storage products.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    interface:
      fw_policy_in: ACCEPT
      fw_policy_out: ACCEPT
      fw_rules_set: null
      interface: eth0
      ipv4: 176.124.106.104
      ipv6: 2001:67c:744:1::22
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Action result information.
  returned: always
  type: str
  sample:
    - All Volumes info for server id : 234.
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class PublicInterfaceInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.server_id = module.params.get('server_id')
        if self.state == "present":
            self.present()

    def present(self):
        interface = self.get_public_interface_for_server(self.server_id)
        self.module.exit_json(
            changed=False,
            msg=f"All Volumes info for server id : ({self.server_id})",
            interfaces=interface,
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        server_id=dict(type="int", required=True),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    PublicInterfaceInformation(module)


if __name__ == '__main__':
    main()
