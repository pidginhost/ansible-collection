# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: generations_info

short_description: List server hardware generations.

version_added: 0.4.0

description:
  - List the hardware generations a server can run on.
  - Pass the slug as the generation of M(pidginhost.cloud.server), or to filter M(pidginhost.cloud.packages_info).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_generations_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: List hardware generations
  pidginhost.cloud.generations_info:
  register: result
"""

RETURN = r"""
generations:
  description:
    - Hardware generations.
  returned: success
  type: list
  elements: dict
  sample:
    - slug: gen2
      name: Generation 2
      description: Newer CPUs
      cpu_label: AMD EPYC
      price_multiplier: "1.20"
      is_default: true
      free_tier_eligible: false
      dedicated_cpu: false
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(argument_spec=pidginhost_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, generations=PidginHostAPI(module).list("/api/cloud/generations/"))


if __name__ == "__main__":
    main()
