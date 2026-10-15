# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: floating_ips_info

short_description: List floating IP addresses.

version_added: 0.4.0

description:
  - List the floating IPv4 and IPv6 addresses in your account.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_floating_ipv4_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  version:
    description:
      - Only list floating IPs of this IP version. Both versions are listed when not set.
    type: int
    choices: [4, 6]
"""

EXAMPLES = r"""
- name: List all floating IPs
  pidginhost.cloud.floating_ips_info:
  register: result

- name: List floating IPv6 addresses
  pidginhost.cloud.floating_ips_info:
    version: 6
"""

RETURN = r"""
floating_ips:
  description: Every floating IP, IPv4 first. Each item has an added C(version) key, 4 or 6.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 3
      version: 4
      address: 203.0.113.5
      gateway: 203.0.113.1
      prefix: 24
      reverse_dns: www.example.com
      label: web-vip
      authorized_vm_count: 2
      created_at: "2026-01-01T00:00:00Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            version=dict(type="int", choices=[4, 6]),
        ),
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    versions = [module.params["version"]] if module.params["version"] else [4, 6]
    module.exit_json(changed=False, floating_ips=[
        dict(item, version=v) for v in versions for item in api.list("/api/cloud/floating-ipv%d/" % v)])


if __name__ == "__main__":
    main()
