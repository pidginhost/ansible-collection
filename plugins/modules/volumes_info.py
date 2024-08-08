# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volumes_info

short_description: List all of storage volumes available on your account

version_added: 0.2.0

description:
  - List all of the storage volumes available on your account.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_list).

author:
  - Popescu Andrei Cristian (@shbpty)

"""

EXAMPLES = r"""
- name: Print all volumes info
 pidginhost.cloud.volumes_info:
   state: present
   token: "{{ pidgin_host_token }}"


- name: Print volumes info for specific Server id
 pidginhost.cloud.volumes_info:
   state: present
   server_id: 23423
   token: "{{ pidgin_host_token }}"
"""

RETURN = """
volumes:
  description:
    - Represents the information about volumes.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    msg: "All Volumes info"
    volumes:
      - alias: "Volume1"
        attached: false
        id: 109
        product: "fast-storage"
        project: ""
        server: ""
        size: 28
      - alias: "Volume2"
        attached: false
        id: 102
        product: "fast-storage"
        project: "zz"
        server: ""
        size: 100
      - alias: "Volume3"
        attached: false
        id: 103
        product: "fast-storage"
        project: ""
        server: ""
        size: 70
      - alias: "Volume4"
        attached: false
        id: 106
        product: "fast-storage"
        project: ""
        server: ""
        size: 24
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: All Volumes info or Volumes info for server.
  returned: always
  type: str
  sample:
    - All Volumes info for server id : (122)
    - All Volumes info.
    - No Server volumes.
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
