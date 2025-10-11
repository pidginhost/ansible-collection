# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volume

short_description: Create or delete volumes.

version_added: 0.2.0

description:
  - Create or delete storage volumes.
  - View the create API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_servers_volumes_create).
  - View the delete API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_servers_destroy).
  - Use volumes_products_info to discover available products.

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  volume_alias:
    description:
      - Alias to assign to the volume.
    type: str
    required: true
  size_gigabytes:
    description:
      - Size of the volume in GiB.
      - Required when C(state=present).
    type: int
    required: false
  product:
    description:
      - Volume product slug.
      - Required when C(state=present).
    type: str
    required: false
  hostname:
    description:
      - Hostname of the server the volume will attach to.
      - Required when C(state=present).
    type: str
    required: false
  project:
    description:
      - Project name associated with the volume.
    type: str
    required: false
"""

EXAMPLES = r"""
- name: Add volume to Server
  pidginhost.cloud.volume:
    state: present
    project: "str"
    product: "fast-storage"
    hostname: hostname.com
    volume_alias: alias
    size_gigabytes: 10

- name: Delete volume
  pidginhost.cloud.volume:
    state: absent
    volume_alias: alias
"""


from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class Volume(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.project = module.params.get("project")
        self.size_gigabytes = module.params.get("size_gigabytes")
        self.product = module.params.get("product")
        self.hostname = module.params.get("hostname")
        self.volume_alias = module.params.get("volume_alias")

        self.arguments_max_length(alias=self.volume_alias)
        products_data = self.check_if_products_exist(self.product)
        self.volume_minim_max(size_gigabytes=self.size_gigabytes, product=self.product, products_data=products_data)

        if self.state == "present":
            self.present()
        elif self.state == "absent":
            self.absent()

    def get_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named with hostname {self.hostname}",
                volume=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                volume=[],
            )
        return servers[0]

    def get_detached_volume(self):
        detached_volumes = list()
        data = self.get_volumes_info(self.SUCCESS_CODE)
        volumes = self.check_if_just_one(data=data, name=self.volume_alias, check_name="alias")

        for volume in volumes:
            if volume["attached"] is False:
                detached_volumes.append(volume)
        if len(detached_volumes) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No detached volume with alias {self.volume_alias}",
                volume=[],
            )
        elif len(volumes) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple detached volumes ({len(detached_volumes)}) with alias ({self.volume_alias})",
                volume=[],
            )
        return detached_volumes[0]

    def present(self):
        server = self.get_server_by_hostname()

        body = {
            "project": self.project,
            "alias": self.volume_alias,
            "size": self.size_gigabytes,
            "product": self.product
        }
        if self.module.check_mode:
            self.module.exit_json(
                changed=True,
                msg=f"Volume will be added to ({self.hostname}) with id : ({server['id']})",
                volume=[],
            )
        volume = self.add_volume_to_server(server['id'], body)
        self.module.exit_json(
            changed=True,
            msg=f"Add volume to ({volume['alias']}) attached to server: ({self.hostname}) with id : ({server['id']})",
            volume=volume,
        )

    def absent(self):
        volume = self.get_detached_volume()
        if self.module.check_mode:
            self.module.exit_json(
                changed=True,
                msg=f"Volume ({self.volume_alias}) would be deleted",
                volume=volume,
            )
        else:
            self.delete_volume(volume['id'])
            self.module.exit_json(
                changed=True,
                msg=f"Deleted volume ({self.volume_alias})",
                volume=volume,
            )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(project=dict(type="str", required=False),
                         size_gigabytes=dict(type="int", required=False),
                         product=dict(type="str", required=False),
                         hostname=dict(type="str", required=False),
                         volume_alias=dict(type="str", required=True)
                         )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["product"]),
            ("state", "present", ["size_gigabytes"]),
            ("state", "absent", ["volume_alias"]),
            ("state", "present", ["hostname"])
        ],
    )
    Volume(module)


if __name__ == "__main__":
    main()
