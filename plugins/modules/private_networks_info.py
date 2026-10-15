# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: private_networks_info

short_description: List private networks.

version_added: 0.4.0

description:
  - List the private networks in your account.
  - The C(servers) list of each network is for display only. Use M(pidginhost.cloud.servers_info) or the
    C(networks.private) list of a server to see its memberships.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_private_networks_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: List private networks
  pidginhost.cloud.private_networks_info:
  register: result
"""

RETURN = r"""
private_networks:
  description: Every private network.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 5
      slug: 198.51.100.0/24
      address: 198.51.100.0/24
      gateway: 198.51.100.1
      provisioned: true
      servers:
        - server: web1.example.com
          address: 198.51.100.10
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(argument_spec=pidginhost_argument_spec(), supports_check_mode=True)
    api = PidginHostAPI(module)
    module.exit_json(changed=False, private_networks=api.list("/api/cloud/private-networks/"))


if __name__ == "__main__":
    main()
