# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ips_info

short_description: List public IP addresses.

version_added: 0.2.0

description:
  - List the public IPv4 or IPv6 addresses in your account.
  - Floating IP addresses are not included. See M(pidginhost.cloud.floating_ips_info).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_ipv4_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info

options:
  ip_type:
    description:
      - The IP version to list.
    type: str
    required: true
    choices: [ipv4, ipv6]
"""

EXAMPLES = r"""
- name: List IPv4 addresses
  pidginhost.cloud.ips_info:
    ip_type: ipv4
  register: result

- name: List IPv6 addresses
  pidginhost.cloud.ips_info:
    ip_type: ipv6
"""

RETURN = r"""
ips:
  description: Every address of the requested version.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 7
      slug: 192.0.2.10
      address: 192.0.2.10
      gateway: 192.0.2.1
      prefix: 24
      attached: true
      server: web1.example.com
      server_id: 12345
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=info_argument_spec(
            ip_type=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
        ),
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    module.exit_json(changed=False, ips=api.list("/api/cloud/%s/" % module.params["ip_type"]))


if __name__ == "__main__":
    main()
