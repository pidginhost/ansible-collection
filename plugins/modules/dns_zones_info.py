# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns_zones_info

short_description: List FreeDNS zones.

version_added: 0.4.0

description:
  - List the domains with FreeDNS hosting active in the account.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/freedns/freedns_dns_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: List FreeDNS zones
  pidginhost.cloud.dns_zones_info:
  register: result
"""

RETURN = r"""
zones:
  description:
    - FreeDNS zones.
    - C(source) is V(internal) for domains registered with PidginHost and V(external) for domains added by the user.
  returned: success
  type: list
  elements: dict
  sample:
    - domain: example.com
      active: true
      source: internal
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(argument_spec=pidginhost_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, zones=PidginHostAPI(module).list("/api/freedns/dns/"))


if __name__ == "__main__":
    main()
