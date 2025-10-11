# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: public_interface_info

short_description: Retrieve the public interface for a server.

version_added: 0.2.0

description:
  - Retrieve the public interface for a server by its identifier.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_public_interface_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  server_id:
    description:
      - Identifier of the server whose public interface should be returned.
    type: int
    required: true
"""

EXAMPLES = r"""
- name: Retrieve public interface information
  pidginhost.cloud.public_interface_info:
    state: present
    server_id: 624
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
            msg="Public interface information retrieved.",
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
