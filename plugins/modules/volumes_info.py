# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volumes_info

short_description: List storage volumes available on your account.

version_added: 0.2.0

description:
  - List storage volumes available on your account or for a specific server.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  server_id:
    description:
      - Restrict the result to volumes attached to the given server identifier.
    type: int
    required: false
"""

EXAMPLES = r"""
- name: Print all volumes info
  pidginhost.cloud.volumes_info:
    state: present

- name: Print volumes info for specific Server id
  pidginhost.cloud.volumes_info:
    state: present
    server_id: 23423
"""


from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class ServersVolumesInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.server_id = module.params.get('server_id')
        if self.state == "present":
            self.present()

    def present(self):
        if self.server_id:
            volumes = self.get_volumes_info_server(self.SUCCESS_CODE, self.server_id)
            self.module.exit_json(
                changed=False,
                msg=f"All Volumes info for server id : ({self.server_id})",
                volumes=volumes,
            )
        volumes = self.get_volumes_info(self.SUCCESS_CODE)
        self.module.exit_json(
            changed=False,
            msg="All Volumes info",
            volumes=volumes,
        )
        self.module.exit_json(changed=False, msg="No Server volumes", volumes=[])


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        server_id=dict(type="int", required=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    ServersVolumesInformation(module)


if __name__ == '__main__':
    main()
