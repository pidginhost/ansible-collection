# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volume

short_description: Add or Delete Volume

version_added: 0.2.0

description:
  - Creates or deletes volumes.
  - View the create API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_servers_volumes_create).
  - View the delete API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_servers_destroy).
  - To check storage available products use volumes_products_info

author:
  - Popescu Andrei Cristian (@shbpty)

options:
 volume_alias:
   description:
     - The alias name of the Volume.
   type: str
   required: true
   when: state == "absent"
 size_gigabytes:
   description:
     - The size of the storage volume in GiB
   type: int
   required: true
   when: state == "present"
 product:
    description:
      - The type of volume being created
    type: str
    required: true
    when: state == "present"
 hostname:
   description:
     - The hostname of the Server.
   type: str
   required: true
   when: state == "present"
 product:
   description:
     - The type of storage product.
   type: str
   required: true
   when: state == "present"
   choices:
     - fast-storage
     - ultra-fast-storage
 project:
   description:
     - The project name.
   type: str
   required: false
"""

EXAMPLES = r"""
- name: Add volume to Server
 pidginhost.cloud.volume:
   token: "{{ pidgin_host_token }}"
   state: present
   project: "str"
   product: "fast-storage"
   hostname: hostname.com
   volume_alias: alias
   size_gigabytes: 10

- name: Delete volume
 pidginhost.cloud.volume:
   token: "{{ pidgin_host_token }}"
   state: absent
   volume_alias: alias
"""

RETURN = """
volume:
  description:
    - Represents action on volume.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    volume:
      alias: "Volume4444"
      attached: true
      id: 127
      product: "fast-storage"
      project: "z5"
      server: "hhtest22332.com"
      size: 50

error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Action information.
  returned: always
  type: str
  sample:
    - Deleted volume (VOLUME_ALIAS).
    - No Product named PRODUCT, available products: LIST_OF_ALL_PRODUCTS.
    - No Server named with hostname HOSTNAME.
    - Multiple Servers (11) found, with hostname: (HOSTNAME)
    - No detached volume with alias VOLUME_ALIAS
    - Multiple detached volumes (11) with alias (VOLUME_ALIAS)
    - Volume will be added to (HOSTNAME) with id : (11)
    - Add volume to (VOLUME_ALIAS) attached to server: (HOSTNAME) with id : (1212)
    - Volume (VOLUME_ALIAS) would be deleted
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
                         volume_alias=dict(type="str", required=False)
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
