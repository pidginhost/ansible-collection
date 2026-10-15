# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volumes_products_info

short_description: List storage volume products.

version_added: 0.2.0

description:
  - List the storage products available for volumes, with their size limits.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_storage_products_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info
"""

EXAMPLES = r"""
- name: List volume products
  pidginhost.cloud.volumes_products_info:
  register: result
"""

RETURN = r"""
volumes:
  description:
    - Storage products.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 3
      slug: fast-storage
      name: Fast storage
      type: storage
      unit: GB
      price: "0.10"
      min_size: 10
      max_size: 1000
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(argument_spec=info_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, volumes=PidginHostAPI(module).list("/api/cloud/storage-products/"))


if __name__ == "__main__":
    main()
