# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: profile_info

short_description: Retrieve the account profile.

version_added: 0.2.0

description:
  - Retrieve the profile of the account that owns the API token.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_profile_retrieve).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info
"""

EXAMPLES = r"""
- name: Retrieve the account profile
  pidginhost.cloud.profile_info:
  register: result
"""

RETURN = r"""
account:
  description:
    - Account profile.
  returned: success
  type: dict
  sample:
    first_name: Jane
    last_name: Doe
    phone: "+40000000000"
    funds: "25.0000"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(argument_spec=info_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, account=PidginHostAPI(module).get("/api/account/profile"))


if __name__ == "__main__":
    main()
