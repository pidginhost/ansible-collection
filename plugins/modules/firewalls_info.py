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

"""


EXAMPLES = r"""
- name: List all firewall on your account
  pidginhost.cloud.firewalls_info:
    token: "{{ pidgin_host_token }}"
    state: present
"""


RETURN = r"""
server:
  description: 
    - Firewalls data.
  type: dict
  returned: always
  sample:
    changed: true
    failed: false
    firewalls:
    - id: 58
      name: "string"
      read_only: false
      rules: []
      status: "validated"
    - id: 45
      name: "Free tier FW"
      read_only: true
      rules:
        - action: "ACCEPT"
          destination: ""
          direction: "in"
          dport: "22,80,443"
          enabled: true
          error_message: ""
          has_error: false
          id: 49
          position: 0
          protocol: "tcp"
          source: ""
          sport: ""
      status: "validated"
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
    - Current firewalls
    - No firewalls.
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
