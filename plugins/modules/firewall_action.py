# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewall_action

short_description: Apply a firewall rule set to a server.

version_added: 0.2.0

description:
  - Attach an existing firewall rule set to a server.
  - View the API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_public_interface_retrieve).
author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
options:
  server_hostname:
    description:
      - Server hostname.
    type: str
    required: true
  rules_set_name:
    description:
      - Rules set name.
      - Required when C(state=present).
    type: str
    required: false
  policy_in:
    description:
      - Defines the action to be taken for incoming traffic, such as ACCEPT, REJECT, DROP.
      - Required when C(state=present).
    type: str
    required: false
    choices:
      - ACCEPT
      - DROP
      - REJECT
  policy_out:
    description:
      - Defines the action to be taken for outgoing traffic.
      - Required when C(state=present).
    type: str
    required: false
    choices:
      - ACCEPT
      - DROP
      - REJECT
"""

EXAMPLES = r"""
- name: Add public interface to server
  pidginhost.cloud.firewall_action:
    state: present
    policy_in: ACCEPT
    policy_out: ACCEPT
    server_hostname: hostname
    rules_set_name: name
"""


from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class Firewall(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.hostname = module.params.get("server_hostname")
        self.policy_in = module.params.get("policy_in")
        self.policy_out = module.params.get("policy_out")
        self.rules_set_name = module.params.get("rules_set_name")
        self.arguments_max_length(rules_set_name=self.rules_set_name, hostname=self.hostname)
        if self.state == "present":
            self.present()

    def get_firewalls(self):
        data = self.get_firewalls_info(self.SUCCESS_CODE)
        firewalls = self.check_if_just_one(data=data, name=self.rules_set_name, check_name="name",
                                           list_name="firewalls")
        if len(firewalls) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Firewall named  ({self.rules_set_name})",
                firewall=[],
            )
        elif len(firewalls) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Firewalls ({len(firewalls)}) found, with name ({self.rules_set_name})",
                firewall=[],
            )
        return firewalls[0]

    def find_server_by_hostname(self):
        data = self.get_cloud_servers_data(self.SUCCESS_CODE)
        servers = self.check_if_just_one(data=data, name=self.hostname, check_name="hostname", list_name="results")
        if len(servers) == 0:
            self.module.fail_json(
                changed=False,
                msg=f"No Server named with hostname {self.hostname}",
                firewall=[],
            )
        elif len(servers) > 1:
            self.module.fail_json(
                changed=False,
                msg=f"Multiple Servers ({len(servers)}) found, with hostname: ({self.hostname})",
                firewall=[],
            )
        return servers[0]

    def present(self):
        if self.module.check_mode:
            self.module.exit_json(
                changed=False,
                msg=f"Firewall rules set {self.rules_set_name} would be applied to server {self.hostname}",
                firewall=[],
            )

        body = {
            "fw_rules_set": self.rules_set_name,
            "fw_policy_in": self.policy_in,
            "fw_policy_out": self.policy_out
        }

        server = self.find_server_by_hostname()
        self.add_public_interface(body, server["id"])
        self.module.exit_json(
            changed=True,
            msg=f"Firewall rules set {self.rules_set_name} has been applied to server {self.hostname}",
            firewall=[],
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        server_hostname=dict(type="str", required=True),
        rules_set_name=dict(type="str", required=False),
        policy_in=dict(type="str", required=False, choices=["ACCEPT", "DROP", "REJECT"]),
        policy_out=dict(type="str", required=False, choices=["ACCEPT", "DROP", "REJECT"]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["policy_in"]),
            ("state", "present", ["policy_out"]),
            ("state", "present", ["rules_set_name"]),
        ],
    )
    Firewall(module)


if __name__ == "__main__":
    main()
