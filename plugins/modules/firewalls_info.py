# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewalls_info

short_description: List all firewall on your account.

version_added: 0.2.0

description:
  - List all firewall on your account.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_firewall_rules_set_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: List all firewall on your account
  pidginhost.cloud.firewalls_info:
    state: present
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class FirewallsInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        firewalls = self.get_firewalls_info(self.SUCCESS_CODE)
        if firewalls:
            self.module.exit_json(
                changed=False,
                msg="Current firewalls",
                firewalls=firewalls,
            )
        self.module.exit_json(changed=False, msg="No firewalls", firewalls=[])


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    FirewallsInformation(module)


if __name__ == "__main__":
    main()
