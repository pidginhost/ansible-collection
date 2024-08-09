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
"""

EXAMPLES = r"""
- name: Print all volumes Products
  pidginhost.cloud.volumes_products_info:
    state: present
    token: "{{ pidgin_host_token }}"
  register: result
"""

RETURN = r"""
volumes:
  description: 
    - Represents the information about storage products.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    volumes:
      count: 2
      next: null
      previous: null
      results:
        - id: 10
          max_size: 100
          min_size: 10
          name: "NVMe Storage"
          price: "0.5000"
          slug: "ultra-fast-storage"
          type: "Ultra fast storage"
          unit: "GB"
        - id: 11
          max_size: 1000
          min_size: 10
          name: "SSD Storage"
          price: "0.1000"
          slug: "fast-storage"
          type: "Fast storage"
          unit: "GB"
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Volume result information.
  returned: always
  type: str
  sample:
    - Storage Products info.
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
            msg=f"Storage Products info. ",
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
