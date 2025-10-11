# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_keys_info

short_description: Print SSH Keys info

version_added: 0.2.0

description:
  - Print SSH Keys info.
  - View the SSH Keys info documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_list).
author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

"""

EXAMPLES = r"""
- name: Print SSH Keys info
  pidginhost.cloud.ssh_keys_info:
    state: present
  register: result
"""


from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class SSHKeysInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        ssh_keys = self.get_ssh_keys()
        if ssh_keys:
            self.module.exit_json(
                changed=False,
                msg="Current SSH keys",
                ssh_keys=ssh_keys.get("results"),
            )
        self.module.exit_json(changed=False, msg="No SSH keys", ssh_keys=[])


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    SSHKeysInformation(module)


if __name__ == '__main__':
    main()
