# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: images_info

short_description: List server OS images.

version_added: 0.2.0

description:
  - List the operating system images available for new servers.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_images_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info
"""

EXAMPLES = r"""
- name: List images
  pidginhost.cloud.images_info:
  register: result
"""

RETURN = r"""
images:
  description:
    - OS images.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 12
      slug: ubuntu24
      name: Ubuntu 24.04
      family_name: Ubuntu
      is_default: true
      default_username: ubuntu
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(argument_spec=info_argument_spec(), supports_check_mode=True)
    module.exit_json(changed=False, images=PidginHostAPI(module).list("/api/cloud/images/"))


if __name__ == "__main__":
    main()
