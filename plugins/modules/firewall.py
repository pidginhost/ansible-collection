# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewall

short_description: Create firewalls rules set, add rules to rules set or delete rules set.

version_added: 0.2.0

description:
  - Create firewalls rules set, add rules to rules set or delete rules set.
  - |
    PidginHost Cloud Firewalls provide the ability to restrict network access to and from a
    Server allowing you to define which ports will accept inbound or outbound connections.
  - View the create firewall rules set API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_firewall_rules_set_create).
  - View the add rules API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_firewall_rules_set_rules_create).
author:
  - Popescu Andrei Cristian (@shbpty)

options:
  create_rules_set:
    description:
      - If you want to create a rules set.
    type: bool
    required: false
  rules_set_name:
    description:
      - A human-readable name for a firewall rules set.
      - The name must be no more the 200 characters long.
    type: str
    required: true
  direction:
    description:
      - Specifies that the rule is for incoming traffic: IN, OUT.
    type: str
    required: false
  action:
    description:
      - Defines the action to be taken for incoming traffic, such as ACCEPT, REJECT, DROP.
    type: str
    required: false
  protocol:
    description:
      - Specifies the network protocol (e.g., TCP, UDP) that the rule applies to.
    type: str
    required: false
  source:
    description:
      - Defines the source of the incoming traffic (e.g., IP address).
    type: str
    required: false
  sport:
    description:
      - Specifies the source port for the incoming traffic.
    type: str
    required: false
  destination:
    description:
      - Specifies the destination of the incoming traffic (e.g., IP address).
    type: str
    required: false
  dport:
    description:
      - Specifies the destination port for the incoming traffic.
    type: str
    required: false
  enabled:
    description:
      - Indicates whether the rule is enabled (true) or disabled (false).
    type: bool
    required: false
    
  position:
    description:
      - Determines the position of the rule in the rule set, possibly based on priority or rule order.
    type: str
    required: false
"""

EXAMPLES = r"""
- name: Delete firewall (rules set)
  pidginhost.cloud.firewall:
    token: "{{ pidgin_host_token }}"
    state: absent
    rules_set_name: Firewall rules set name
    
- name: Create firewall (rules set)
  pidginhost.cloud.firewall:
    token: "{{ pidgin_host_token }}"
    state: present
    create_rules_set: true
    rules_set_name: Firewall rules set name

- name: Add firewall rules to (rules set)
  pidginhost.cloud.firewall:
    token: "{{ pidgin_host_token }}"
    state: present
    rules_set_name: New Firewall1
    create_rules_set: false
    direction: in
    action: ACCEPT
    protocol: tcp
    source: str
    sport: str
    destination: str
    dport: 22
    enabled: true
    position: 0
"""

RETURN = r"""
firewall:
  description:
    - Create firewall (rules set)
  type: dict
  returned: always
  sample:
    module_args:
      action: null
      create_rules_set: true
      destination: null
      direction: null
      dport: null
      enabled: null
      position: null
      protocol: null
      rules_set_name: Firewall rules set name22222
      source: null
      sport: null
      state: present
      timeout: 300
      token: VALUE_SPECIFIED_IN_NO_LOG_PARAMETER
    
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
    - Firewall rules set RULES_SET_NAME (34543) has been be deleted
    - For 'state'='state', both 'direction' and 'action' are required when 'create_rules_set' is RULES_SET_NAME.
    - No Firewall named  (RULES_SET_NAME)
    - Multiple Firewalls (345) found, with name (RULES_SET_NAME)
    - Firewall rules set RULES_SET_NAME would be created
    - Firewall rules set RULES_SET_NAME has been created
    - New rules will be added for RULES_SET_NAME
    - Firewall rules has been added for RULES_SET_NAME
    - Firewall rules set RULES_SET_NAME (24234) would be deleted
    - Firewall rules set RULES_SET_NAME (23432) has been be deleted
"""

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions


class Firewall(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.create_rules_set = module.params.get("create_rules_set")
        self.rules_set_name = module.params.get("rules_set_name")
        self.direction = module.params.get("direction")
        self.action = module.params.get("action")
        self.protocol = module.params.get("protocol")
        self.source = module.params.get("source")
        self.sport = module.params.get("sport")
        self.destination = module.params.get("destination")
        self.dport = module.params.get("dport")
        self.enabled = module.params.get("enabled")
        self.position = module.params.get("position")
        self.arguments_max_length(rules_set_name=self.rules_set_name, protocol=self.protocol,
                                  source=self.source, sport=self.sport,
                                  destination=self.destination, dport=self.dport)
        if self.state == "present":
            self.present()
        elif self.state == "absent":
            self.absent()

        if self.state == "present" and not (self.direction and self.action) and not self.create_rules_set:
            self.module.fail_json(
                changed=False,
                msg=f"For 'state'='{self.state}', both 'direction' and 'action'"
                    f" are required when 'create_rules_set' is {self.create_rules_set}.",
                firewall=[],
            )

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

    def rules_set(self):
        body = {
            "name": self.rules_set_name,
        }
        self.create_firewall_rules_set(body)

    def add_rules_set(self):
        firewall = self.get_firewalls()
        rules_set_id = firewall.get('id')
        body = {
            "direction": self.direction,
            "action": self.action,
            "protocol": self.protocol,
            "source": self.source,
            "sport": self.sport,
            "destination": self.destination,
            "dport": self.dport,
            "enabled": self.enabled,
            "position": self.position
        }
        body = self.return_valid_body_items(body)

        self.add_firewall_rules(body, rules_set_id)

    def present(self):
        if self.create_rules_set:
            if self.module.check_mode:
                self.module.exit_json(
                    changed=False,
                    msg=f"Firewall rules set {self.rules_set_name} would be created",
                    firewall=[],
                )

            self.rules_set()
            self.module.exit_json(
                changed=True,
                msg=f"Firewall rules set {self.rules_set_name} has been created",
                firewall=[],
            )
        else:
            if self.module.check_mode:
                self.module.exit_json(
                    changed=False,
                    msg=f"New rules will be added for {self.rules_set_name}",
                    firewall=[],
                )

            self.add_rules_set()
            self.module.exit_json(
                changed=True,
                msg=f"Firewall rules has been added for {self.rules_set_name}",
                firewall=[],
            )

    def absent(self):
        firewall = self.get_firewalls()
        if self.module.check_mode:
            self.module.exit_json(
                changed=False,
                msg=f"Firewall rules set {self.rules_set_name} ({firewall['id']}) would be deleted",
                firewall=firewall,
            )

        self.delete_firewall_rules_set(firewall['id'])
        self.module.exit_json(
            changed=False,
            msg=f"Firewall rules set {self.rules_set_name} ({firewall['id']}) has been be deleted",
            firewall=firewall,
        )


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        create_rules_set=dict(
            type=bool,
            choices=[True, False],
            default=False),
        rules_set_name=dict(type="str", required=True),
        direction=dict(type="str", required=False, choices=["in", "out"]),
        action=dict(type="str", required=False, choices=["ACCEPT", "DROP", "REJECT"]),
        protocol=dict(type="str", required=False),
        source=dict(type="str", required=False),
        sport=dict(type="str", required=False),
        destination=dict(type="str", required=False),
        dport=dict(type="str", required=False),
        enabled=dict(type=bool, required=False),
        position=dict(type="str", required=False),

    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    Firewall(module)


if __name__ == "__main__":
    main()
