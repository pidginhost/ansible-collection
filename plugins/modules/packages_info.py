# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: packages_info

short_description: Print PidginHost Packages info.

version_added: 0.2.0

description:
  - Print PidginHost Packages info.
  - View the create API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_server_packages_list).

author:
  - Popescu Andrei Cristian (@shbpty)
  
"""

EXAMPLES = r"""
- name: Print public interface
  pidginhost.cloud.packages_info:
    state: present
    token: "{{ pidgin_host_token }}"

"""

RETURN = r"""
account:
  description: 
    - Represents the information about packages products.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    account:
      count: 10
      next: null
      previous: null
      results:
        - id: 12
          name: "CloudV 2"
          slug: "cloudv-2"
        - id: 2
          name: "CloudV 4"
          slug: "cloudv-4"
        - id: 13
          name: "CloudV 1"
          slug: "cloudv-1"
        - id: 5
          name: "CloudV 7"
          slug: "cloudv-7"
        - id: 6
          name: "CloudV 8"
          slug: "cloudv-8"
        - id: 4
          name: "CloudV 6"
          slug: "cloudv-6"
        - id: 1
          name: "CloudV 3"
          slug: "cloudv-3"
        - id: 45
          name: "CloudV 0"
          slug: "cloudv-0"
        - id: 3
          name: "CloudV 5"
          slug: "cloudv-5"
        - id: 7
          name: "CloudV 9"
          slug: "cloudv-9"
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Action result information.
  returned: always
  type: str
  sample:
    - Current account information
    - Current account information not found
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class PackagesInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        packages = self.get_packages_info(self.SUCCESS_CODE)
        if packages:
            self.module.exit_json(
                changed=False,
                msg="Packages information",
                packages=packages,
            )
        self.module.fail_json(
            changed=False, msg="Current packages information not found", packages=[]
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    PackagesInformation(module)


if __name__ == '__main__':
    main()
