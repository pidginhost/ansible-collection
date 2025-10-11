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

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

"""

EXAMPLES = r"""
- name: Print public interface
  pidginhost.cloud.packages_info:
    state: present

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
