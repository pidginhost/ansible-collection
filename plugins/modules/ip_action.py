# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ip_action

short_description: Attach or detach an IP address from a server.

version_added: 0.2.0

description:
  - Attach or detach an IP address from a server.
  - Each server may only have one IPv4 address attached, as well as one IPv6 address.
  - View the attach IPv4 API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_attach_ipv4_create).
  - View the attach IPv6 API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_attach_ipv6_create).
  - View the detach IPv4 API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_detach_ipv4_create).
  - View the detach IPv6 API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_detach_ipv6_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  server_id:
    description:
      - Identifier of the server to target. Ignored when C(server_hostname) is provided.
    type: int
    required: false

  server_hostname:
    description:
      - Hostname of the server to target. Must be unique when used.
    type: str
    required: false

  ip_address:
    description:
      - IP address to attach or detach.
    type: str
    required: true

  server_ip:
    description:
      - Server IP identifier returned by the API. Required when attaching an IP.
    type: str
    required: false
"""

EXAMPLES = r"""
- name: Attach IP to server by hostname
  pidginhost.cloud.ip_action:
    state: present
    server_hostname: hostname
    ip_address: 192.0.2.10

- name: Attach IP to server by id
  pidginhost.cloud.ip_action:
    state: present
    server_id: 42
    ip_address: 198.51.100.5

- name: Detach IP from server
  pidginhost.cloud.ip_action:
    state: absent
    ip_address: 198.51.100.5
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class IpsAction(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.ip_address = module.params.get('ip_address')
        self.server_id = module.params.get("server_id")
        self.hostname = module.params.get("server_hostname")
        if self.server_id:
            self.server = self.find_server_by_id()
        if self.hostname and not self.server_id:
            self.server = self.find_server_by_hostname()
            self.server_id = self.server["id"]

        self.ips_info, self.ip_type = self.validate_ip(self.ip_address)
        self.ip_id = None
        self.server_hostname = None
        self.attached = None
        self.address = None
        if self.state == "present":
            self.present()
        elif self.state == "absent":
            self.absent()

    def check_if_ip(self):
        data = self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
        networks = data.get("networks", {}).get("public", {})
        if networks.get(self.ip_type):
            self.module.fail_json(
                changed=False,
                msg=f"Server already have attached an ({self.ip_type})",
                ip_result=[],
            )

    def find_server_by_id(self):
        if self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE):
            return self.get_cloud_server_data_by_id(self.server_id, self.SUCCESS_CODE)
        self.module.fail_json(
            changed=False,
            msg=f"No Server with ID ({self.server_id})",
            ip_result=[],
        )

    def present(self):
        self.attach_ip()

    def absent(self):
        self.detach_ip()

    def find_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named with hostname {self.hostname}",
                ip_result=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                ip_result=[],
            )
        return servers[0]

    def attach_ip(self):
        for ip in self.ips_info.get("results"):
            if ip["address"] == self.ip_address:
                self.ip_id = ip["id"]
                self.attached = ip["attached"]
                self.address = ip["address"]

        if self.address:
            if self.module.check_mode:
                if self.attached:
                    self.module.fail_json(
                        changed=False,
                        msg=f'IP ({self.address}) attached.',
                        ip_result=[],
                    )

                else:
                    self.module.fail_json(
                        changed=False,
                        msg=f'IP ({self.address}) will be attached to server ({self.hostname}).',
                        ip_result=[],
                    )
            if self.attached:
                self.module.fail_json(
                    changed=False,
                    msg=f'IP ({self.address}) attached.',
                    ip_result=[],
                )
            else:
                body = {
                    self.ip_type: self.ip_address

                }
                self.check_if_ip()
                ip_result = self.attach_ip_by_id(self.server_id, self.ip_type, body)
                self.module.exit_json(
                    changed=True,
                    msg=f"IP ({self.ip_address}) attached to ({self.hostname})",
                    ip_result=ip_result,
                )
        else:
            self.module.fail_json(
                changed=False,
                msg=f'IP ({self.ip_address}) is not in your ips.',
                ip_result=[],
            )

    def detach_ip(self):
        for ip in self.ips_info.get("results"):
            if ip["address"] == self.ip_address:
                self.ip_id = ip["id"]
                self.server_hostname = ip["server"]
                self.attached = ip["attached"]
                self.address = ip["address"]
        if self.address:
            if self.module.check_mode:
                if self.attached:
                    self.module.exit_json(
                        changed=False,
                        msg=f'IP ({self.address}) will be detached from '
                            f'server ({self.server_hostname})',
                        ip_result=[],
                    )

                else:
                    self.module.fail_json(
                        changed=False,
                        msg=f'IP ({self.address}) detached from server.',
                        ip_result=[],
                    )
            if self.attached:
                body = {
                }
                ip_result = self.detach_ip_by_id(self.ip_type, self.ip_id, body)
                self.module.exit_json(
                    changed=True,
                    msg=f'IP ({self.address}) detached from server ({self.server_hostname})',
                    ip_result=ip_result,
                )
            else:
                self.module.fail_json(
                    changed=False,
                    msg=f'IP ({self.address}) detached from server.',
                    ip_result=[],
                )
        else:
            self.module.fail_json(
                changed=False,
                msg=f'IP ({self.ip_address}) is not in your ips.',
                ip_result=[],
            )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        server_id=dict(type="int", required=False),
        ip_address=dict(type="str", required=True),
        server_hostname=dict(type="str", required=False),
        server_ip=dict(type="str", required=False),

    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("server_id", "server_hostname")],
    )
    IpsAction(module)


if __name__ == "__main__":
    main()
