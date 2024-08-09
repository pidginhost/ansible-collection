# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_action_resize

short_description: Resize a Server Volume or upgrade Server package

version_added: 0.2.0

description:
  - Resize a Server Volume.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_volumes_partial_update).
  - Upgrade Server package.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/v1/v1_cloud_servers_modify_package_create).
  - Run package_info module to check the available packages.
author:
  - Popescu Andrei Cristian (@shbpty)


options:
  server_id:
    description:
      - A unique identifier for a Server instance.
      - If provided, C(server_hostname) is ignored.
    type: int
    required: false
  server_hostname:
    description:
      - The hostname of the Server to act on.
      - If provided, must be unique.
    type: str
    required: false
  disk:
    description:
      - When true, the Server's disk will be resized.
      - This is a permanent change and cannot be reversed as a Server's disk size cannot be decreased.
    type: bool
    required: true
  size_gigabytes:
    description:
      - The gigabytes size to resize the Volume..
    type: int
    required: false
  package_name:
    description:
      - The package slug name of the new package must be higher than the current one.
    type: str
    required: false
  volume_alias:
    description:
      - The alias name of the volume intended for resizing.
    type: str
    required: false
"""

EXAMPLES = r"""
- name: Resize a Server Volume by hostname
 pidginhost.cloud.server_action_resize:
   state: present
   token: "{{ pidgin_host_token }}"
   server_hostname: hhtest22332.com
   disk: true
   size_gigabytes: 60
   volume_alias: Volume4444
   product: fast-storage

- name: Resize a Server Volume by id
 pidginhost.cloud.server_action_resize:
   state: present
   token: "{{ pidgin_host_token }}"
   server_id: 23423
   disk: true
   size_gigabytes: 60
   volume_alias: Volume4444
   product: fast-storage

- name: Upgrade Server package by hostname
 pidginhost.cloud.server_action_resize:
   state: present
   token: "{{ pidgin_host_token }}"
   server_hostname: hhtest22332.com
   disk: false
   package_name: cloudv-3

- name: Upgrade Server package by id
 pidginhost.cloud.server_action_resize:
   state: present
   token: "{{ pidgin_host_token }}"
   server_id: 234234
   disk: false
   package_name: cloudv-3
"""

RETURN = """
action:
    cpus: 8
    disk_size: 200
    hostname: hhtest22332.com
    id: 707
    image: ubuntu22
    machine:
      cpu:
        cores: 8
        usage: 9.06
      memory:
        maxmem: 34359738368
        mem: 121700352
        usage: 0.35
      status: running
      uptime: 7
      uptime_text: 0:00:07
    memory: 32
    networks:
      private: []
      public:
        interface: eth0
        ipv4: 176.124.106.104
        ipv6: 2001:67c:744:1::22
    package: cloudv-6
    project: z5
    status: active
    username: phuser
    volumes:
      - alias: Volume
        attached: true
        id: 123
        product: fast-storage
        project: z5
        server: hhtest22332.com
        size: 17
      - alias: Volume4444
        attached: true
        id: 129
        product: fast-storage
        project: z5
        server: hhtest22332.com
        size: 50
  changed: true
  failed: false

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
    - Package you have chosen is PACKAGE value of package must be one of: PACKAGE_LIST
    - Server HOSTNAME have new package PACKAGE
    - No Server with ID 23423
    - No Server named with hostname HOSTNAME
    - Multiple Servers (23423) found, with hostname: (HOSTNAME)
    - No attached volume with alias: (VOLUME_ALIAS)
    - Multiple attached volumes (23423) with alias: (VOLUME_ALIAS)
    - The volume size is (23) while you selected (11) , resulting in the inability to reduce the volume size.
    - Volume (VOLUME_ALIAS) from Server HOSTNAME (23442) would be sent action 'resize',
      requested size is '55' and current size is 44
    - Volume (VOLUME_ALIAS) from Server HOSTNAME (2323) current size is '55' and last size was 44
  """

import time
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class ServerActionResize(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.product = module.params.get('product')
        self.project = module.params.get('project')
        self.package_name = module.params.get("package_name")
        self.volume_alias = module.params.get("volume_alias")
        self.server_id = module.params.get("server_id")
        self.hostname = module.params.get("server_hostname")
        self.disk = module.params.get("disk")
        self.size_gigabytes = module.params.get("size_gigabytes")
        self.timeout = module.params.get("timeout")

        self.arguments_max_length(alias=self.volume_alias, hostname=self.hostname)

        if self.disk is False:
            package_choices = self.return_packages_choices()
            if self.package_name not in package_choices:
                self.module.fail_json(
                    changed=False,
                    msg=f"Package you have chosen is {self.package_name} value of "
                        f"package must be one of: {package_choices}",
                    action=[],
                )
        if self.disk is True:
            products_data = self.check_if_products_exist(self.product)
            self.volume_minim_max(size_gigabytes=self.size_gigabytes, product=self.product, products_data=products_data)

        if self.server_id:
            self.server = self.find_server_by_id()
            self.server_package = self.server["slug"]
        if self.hostname and not self.server_id:
            self.server = self.find_server_by_hostname()
            self.server_id = self.server["id"]
            self.server_package = self.server["package"]

        if self.state == "present":
            self.present()

    def find_server_by_id(self):
        if self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE):
            return self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
        self.module.fail_json(
            changed=False,
            msg=f"No Server with ID {self.server_id}",
            action=[],
        )

    def find_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named with hostname {self.hostname}",
                action=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                action=[],
            )
        return servers[0]

    def get_volumes(self):
        attached_volumes = list()
        data = self.get_all_volumes_from_server_by_id(self.server_id)
        volumes = self.check_if_just_one(data=data, name=self.volume_alias, check_name="alias", list_name="volumes")
        for volume in volumes:
            if volume["attached"] is True:
                attached_volumes.append(volume)
        if len(attached_volumes) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No attached volume with alias: ({self.volume_alias})",
                action=[],
            )
        elif len(volumes) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple attached volumes ({len(attached_volumes)}) with alias: ({self.volume_alias})",
                action=[],
            )
        return attached_volumes[0]

    def present(self):
        if self.disk is True:
            volume = self.get_volumes()

            if int(volume['size']) >= int(self.size_gigabytes):
                self.module.fail_json(
                    changed=False,
                    msg=(
                        f"The volume size is ({volume['size']}) , "
                        f"while you selected ({self.size_gigabytes}) , "
                        f"resulting in the inability to reduce the volume size."),
                    action=[],
                )
            if self.module.check_mode:
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f"Volume ({volume['alias']}) from Server {volume['server']} ({self.server_id}) "
                        f"would be sent action 'resize', requested size is '{self.size_gigabytes}' and current size is "
                        f"'{volume['size']}'"),
                    action=[],
                )

            body = {

                "alias": self.volume_alias,
                "size": self.size_gigabytes,
                "product": self.product
            }

            if self.project:
                body['project'] = self.project
            action = self.increase_volume(volume['id'], body)
            self.module.exit_json(
                changed=True,
                msg=(
                    f"Volume ({volume['alias']}) from Server {volume['server']} ({self.server_id}) "
                    f"current size is '{self.size_gigabytes}' and last size was "
                    f"'{volume['size']}'"),
                action=action,
            )
        else:
            actual = self.server_package.split('-')[1]
            new = self.package_name.split('-')[1]
            if int(actual) >= int(new):
                self.module.fail_json(
                    changed=False,
                    msg=(
                        f"Chosen package {self.package_name} "
                        f"must be higher than actual package {self.server_package}"),
                    action=[],
                )
            if self.module.check_mode:
                self.module.exit_json(
                    changed=True,
                    msg=(
                        f"Server {self.server['hostname']} will have new package {self.package_name}"),
                    action=[],
                )
            body = {
                "package": self.package_name
            }
            self.modify_package(self.server_id, body)
            server = self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
            end_time = time.monotonic() + self.timeout
            while time.monotonic() < end_time and server['status'] != 'active':
                time.sleep(self.SLEEP)
                server = self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
            self.module.exit_json(
                changed=True,
                msg=(
                    f"Server {self.server['hostname']} have new package {self.server_package}"),
                action=server,
            )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        project=dict(type='str', required=False),
        product=dict(type="str", required=False),
        package_name=dict(type="str", required=False),
        server_id=dict(type="int", required=False),
        server_hostname=dict(type="str", required=False),
        volume_alias=dict(type="str", required=False),
        disk=dict(type="bool", required=True),
        size_gigabytes=dict(type="int", required=False),

    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("server_id", "server_hostname")],
        required_if=[
            ("disk", True, ["size_gigabytes"]),
            ("disk", False, ["package_name"]),
            ("disk", True, ["volume_alias"]),
            ("disk", True, ["product"])
        ],
    )
    ServerActionResize(module)


if __name__ == "__main__":
    main()
