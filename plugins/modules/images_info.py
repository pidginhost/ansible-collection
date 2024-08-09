# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: images_info

short_description: Print Servers images information

version_added: 0.2.0

description:
  - Print Servers images information.
  - View images API info documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_images_list).
author:
  - Popescu Andrei Cristian (@shbpty)


"""

EXAMPLES = r"""
- name: Print all images data
  pidginhost.cloud.images_info:
    token: "{{ pidgin_host_token }}"
    state: present
"""

RETURN = r"""
images:
  description: 
    - Represents the information about images.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    images: 
      count: 5
      next: null
      previous: null
      results:
        - id: 1
          name: "Ubuntu 22.04"
          slug: "ubuntu22"
        - id: 4
          name: "Debian 12"
          slug: "debian12"
        - id: 5
          name: "Rocky Linux 8"
          slug: "rocky8"
        - id: 6
          name: "Rocky Linux 9"
          slug: "rocky9"
        - id: 7
          name: "Ubuntu 24.04"
          slug: "ubuntu24"
            
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: All Volumes info or Volumes info for server.
  returned: always
  type: str
  sample:
    - Current volumes information
    - Current volumes information not found.
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class ImagesInformation(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        if self.state == "present":
            self.present()

    def present(self):
        account_info = self.get_images_info(self.SUCCESS_CODE)
        if account_info:
            self.module.exit_json(
                changed=False,
                msg="Current images information",
                images=account_info,
            )
        self.module.fail_json(
            changed=False, msg="Current images information not found", images=[]
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    ImagesInformation(module)


if __name__ == '__main__':
    main()
