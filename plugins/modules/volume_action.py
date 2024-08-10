# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volume_action

short_description: Attach or detach volume from Server

version_added: 0.2.0

description:
  - Attach or Detach volume from Server.
  - First, the volume needs to be detached and then attached.
  - Each volume may only be attached to a single Server.
  - Detach - view the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_attach_create).
  - Attach - view the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_detach_create).
  - Add size - view the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_volumes_partial_update).

author:
  - Popescu Andrei Cristian (@shbpty)

options:
  volume_alias:
    description:
      - The name of the volume to attach or detach.
    type: str
    required: true
  server_hostname:
    description:
      - The hostname of the Server to attach or detach to the volume to.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Attach volume to Server
  pidginhost.cloud.volume_action:
    state: present
    volume_alias: alias
    server_hostname: hostname.com

- name: Detach volume from Server
  pidginhost.cloud.volume_action:
    state: absent
    volume_alias: alias
    server_hostname: hostname.com
"""

RETURN = r"""
action:
  description: 
    - Attach or detach volume from Server.
  type: dict
  returned: always
  sample:
    changed: false
    failed: false
    action:
      alias: "Volume4444"
      attached: true
      id: 128
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
  description: Volume action information.
  returned: always
  type: str
  sample:
    - No detached volume with alias ALIAS
    - Multiple detached volumes 10 with alias ALIAS
    - Multiple attached volumes 10 with alias ALIAS
    - Multiple Servers 10 found, with hostname: HOSTNAME
    - Volume alias  (ALIAS) id  (191) would be attached to (HOSTNAME) 
    - Attached volume (ALIAS) to (HOSTNAME)
    - Volume alias  (ALIAS) id  (191) would be detached from (HOSTNAME)
    - No attached volume with alias: ALIAS
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class VolumeAction(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.hostname = module.params.get("server_hostname")
        self.volume_alias = module.params.get("volume_alias")
        self.body = dict()
        if self.state == "present":
            self.present()
        elif self.state == "absent":
            self.absent()

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
                action=[],
            )
        elif len(volumes) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple detached volumes ({len(detached_volumes)}) with alias ({self.volume_alias})",
                action=[],
            )
        return detached_volumes[0]

    def get_attached_volume(self):
        attached_volumes = list()
        data = self.get_volumes_info(self.SUCCESS_CODE)
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

    def get_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named {self.hostname}",
                action=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                action=[],
            )
        return servers[0]

    def attach_volume(self):
        volume = self.get_detached_volume()
        server = self.get_server_by_hostname()
        if self.module.check_mode:
            self.module.exit_json(
                changed=True,
                msg=f"Volume alias : ({self.volume_alias}) id : ({volume['id']}) "
                    f"would be attached to ({server['hostname']})",
                action=[],
            )
        body = {
            "vm": server['id'],
        }
        self.attach_volume_by_id(volume['id'], body)
        self.module.exit_json(
            changed=True,
            msg=f"Attached volume ({self.volume_alias}) to ({server['hostname']})",
            action=volume,
        )

    def detach_volume(self):
        volume = self.get_attached_volume()
        server = self.get_server_by_hostname()
        if server["hostname"] == volume["server"]:
            if self.module.check_mode:
                self.module.exit_json(
                    changed=True,
                    msg=f"Volume alias : ({self.volume_alias}) id : ({volume['id']}) "
                        f"would be detached from ({server['hostname']})",
                    action=[],
                )
        else:
            self.module.exit_json(
                changed=False,
                msg=f"Volume alias : ({self.volume_alias}) id : ({volume['id']}) not attached to ({server['hostname']})",
                action=[],
            )

        body = {
            "alias": volume["alias"],
        }
        self.detach_volume_by_id(volume["id"], body)
        self.module.exit_json(
            changed=True,
            msg=f"Detached volume ({self.volume_alias}) from ({server['hostname']})",
            action=volume,
        )

    def present(self):
        self.attach_volume()

    def absent(self):
        self.detach_volume()


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        volume_alias=dict(type="str", required=True),
        server_hostname=dict(type="str", required=False),

    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    VolumeAction(module)


if __name__ == "__main__":
    main()
