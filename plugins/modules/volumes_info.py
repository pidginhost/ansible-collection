# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volumes_info

short_description: List storage volumes.

version_added: 0.2.0

description:
  - List the storage volumes in the account, or the active volumes of one server.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_list).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info

options:
  server_id:
    description:
      - Only list the active volumes of this server.
    type: int
"""

EXAMPLES = r"""
- name: List all volumes
  pidginhost.cloud.volumes_info:
  register: result

- name: List the volumes of one server
  pidginhost.cloud.volumes_info:
    server_id: 12345
"""

RETURN = r"""
volumes:
  description:
    - Volumes.
  returned: success
  type: list
  elements: dict
  sample:
    - id: 321
      alias: data
      project: ""
      size: 50
      product: fast-storage
      attached: true
      server: web1.example.com
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, info_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=info_argument_spec(server_id=dict(type="int")),
        supports_check_mode=True,
    )
    server_id = module.params["server_id"]
    path = "%s%s/volumes/" % (SERVERS, server_id) if server_id else "/api/cloud/volumes/"
    module.exit_json(changed=False, volumes=PidginHostAPI(module).list(path))


if __name__ == "__main__":
    main()
