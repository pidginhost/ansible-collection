# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: profile_info

short_description: Print PidginHost profile info

version_added: 0.2.0

description:
  - Print PidginHost profile info
  - View the create API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_profile_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)
"""

EXAMPLES = r"""
- name: Print public interface
  pidginhost.cloud.profile_info:
    state: present
    
"""

RETURN = r"""
account:
  description: 
    - Represents the information about storage products.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    account:
      first_name: Web
      funds: 999920.41
      last_name: Test
      phone: "0000000000"
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
    - Current account information
    - Current account information not found
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
