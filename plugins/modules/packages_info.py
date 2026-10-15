# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: packages_info

short_description: List server packages.

version_added: 0.2.0

description:
  - List the server packages available for new servers.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_server_packages_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info

options:
  generation:
    description:
      - Only list packages available on this hardware generation slug. See M(pidginhost.cloud.generations_info).
      - Free tier only packages are left out when set.
    type: str
    version_added: 0.4.0
"""

EXAMPLES = r"""
- name: List all packages
  pidginhost.cloud.packages_info:
  register: result

- name: List packages for one hardware generation
  pidginhost.cloud.packages_info:
    generation: gen2
"""

RETURN = r"""
packages:
  description:
    - Server packages.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 4
      slug: cloudv-2
      name: Cloud V2
      cpus: 2
      memory: 4
      disk_size: 50
      traffic: 2
      available_generations: [gen1, gen2]
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, info_argument_spec


def main():
    module = AnsibleModule(argument_spec=info_argument_spec(generation=dict(type="str")), supports_check_mode=True)
    query = drop_none(dict(generation=module.params["generation"]))
    module.exit_json(changed=False, packages=PidginHostAPI(module).list("/api/cloud/server-packages/", **query))


if __name__ == "__main__":
    main()
