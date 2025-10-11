# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: profile_info

short_description: Retrieve PidginHost profile information.

version_added: 0.2.0

description:
  - Retrieve PidginHost profile information.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_profile_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: Retrieve PidginHost profile information
  pidginhost.cloud.profile_info:
    state: present
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class AccountInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        account_info = self.get_account_info(self.SUCCESS_CODE)
        if account_info:
            self.module.exit_json(
                changed=False,
                msg="Current account information",
                account=account_info,
            )
        self.module.fail_json(
            changed=False, msg="Current account information not found", account=[]
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    AccountInformation(module)


if __name__ == '__main__':
    main()
