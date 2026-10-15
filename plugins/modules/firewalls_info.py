# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewalls_info

short_description: List firewall rules sets.

version_added: 0.2.0

description:
  - List every firewall rules set of the account with its rules.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_firewall_rules_set_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info
"""

EXAMPLES = r"""
- name: List firewall rules sets
  pidginhost.cloud.firewalls_info:
  register: result
"""

RETURN = r"""
firewalls:
  description:
    - Firewall rules sets with their rules.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 12
      name: web
      status: validated
      read_only: false
      rules:
        - id: 101
          direction: in
          action: ACCEPT
          protocol: tcp
          source: ""
          sport: ""
          destination: ""
          dport: "22"
          enabled: true
          position: 0
          has_error: false
          error_message: ""
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(argument_spec=info_argument_spec(), supports_check_mode=True)
    firewalls = PidginHostAPI(module).list("/api/cloud/firewall-rules-set/")
    module.exit_json(changed=False, firewalls=firewalls)


if __name__ == "__main__":
    main()
