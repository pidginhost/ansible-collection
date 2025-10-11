# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volumes_products_info

short_description: Print volumes Products info

version_added: 0.2.0

description:
  - Print volumes Products info.
  - View the print volumes Products info documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
"""

EXAMPLES = r"""
- name: Print all volume products
  pidginhost.cloud.volumes_products_info:
    state: present
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class StorageProductsInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        products = self.get_storage_products_info()
        self.module.exit_json(
            changed=False,
            msg="Storage Products info.",
            volumes=products,
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    StorageProductsInformation(module)


if __name__ == '__main__':
    main()
