# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewall

short_description: Manage firewall rules sets and their rules.

version_added: 0.2.0

description:
  - Create or delete a firewall rules set and manage its rules.
  - The rules set is identified by its unique O(name) and is created when missing.
  - A rule is identified by its direction, action, protocol, source, sport, destination and dport. A listed rule
    that is missing is added. A matching rule is updated when its O(rules[].enabled) or O(rules[].position) differ.
  - Use M(pidginhost.cloud.firewall_action) to apply a rules set to a server.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_firewall_rules_set_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the rules set should exist.
    type: str
    choices: [present, absent]
    default: present
  name:
    description:
      - Rules set name. At most 200 characters.
    type: str
    required: true
    aliases: [rules_set_name]
  rules:
    description:
      - Rules the set should contain.
    type: list
    elements: dict
    suboptions:
      direction:
        description:
          - Traffic direction.
        type: str
        required: true
        choices: [in, out]
      action:
        description:
          - Action for matching traffic.
        type: str
        required: true
        choices: [ACCEPT, DROP, REJECT]
      protocol:
        description:
          - Protocol, for example V(tcp) or V(udp). Required when O(rules[].sport) or O(rules[].dport) is set.
        type: str
      source:
        description:
          - Source address. A single IP, a range such as V(192.0.2.10-192.0.2.20) or a comma separated list.
        type: str
      sport:
        description:
          - Source port. A number, a range such as V(80:85) or a comma separated list.
        type: str
      destination:
        description:
          - Destination address, in the same format as O(rules[].source).
        type: str
      dport:
        description:
          - Destination port, in the same format as O(rules[].sport).
        type: str
      enabled:
        description:
          - Whether the rule is active.
        type: bool
        default: true
      position:
        description:
          - Rule position in the set. Not compared when not set.
        type: int
  purge_rules:
    description:
      - Delete rules of the set that are not listed in O(rules) or in the legacy rule options.
    type: bool
    default: false
  direction:
    description:
      - Legacy single rule. When set, O(direction), O(action), O(protocol), O(source), O(sport), O(destination),
        O(dport), O(enabled) and O(position) describe one more rule added to O(rules).
      - Same as O(rules[].direction).
    type: str
    choices: [in, out]
  action:
    description:
      - Legacy single rule action. Required with O(direction). Same as O(rules[].action).
    type: str
    choices: [ACCEPT, DROP, REJECT]
  protocol:
    description:
      - Legacy single rule protocol. Same as O(rules[].protocol).
    type: str
  source:
    description:
      - Legacy single rule source. Same as O(rules[].source).
    type: str
  sport:
    description:
      - Legacy single rule source port. Same as O(rules[].sport).
    type: str
  destination:
    description:
      - Legacy single rule destination. Same as O(rules[].destination).
    type: str
  dport:
    description:
      - Legacy single rule destination port. Same as O(rules[].dport).
    type: str
  enabled:
    description:
      - Legacy single rule state. Treated as V(true) when not set. Same as O(rules[].enabled).
    type: bool
  position:
    description:
      - Legacy single rule position. Same as O(rules[].position).
    type: int
  create_rules_set:
    description:
      - Ignored. The rules set is always created when missing.
    type: bool
"""

EXAMPLES = r"""
- name: Allow SSH and HTTPS in, drop every other rule of the set
  pidginhost.cloud.firewall:
    name: web
    purge_rules: true
    rules:
      - direction: in
        action: ACCEPT
        protocol: tcp
        dport: "22"
        source: 203.0.113.0/24
      - direction: in
        action: ACCEPT
        protocol: tcp
        dport: "443"

- name: Add one rule with the legacy options
  pidginhost.cloud.firewall:
    rules_set_name: web
    direction: in
    action: ACCEPT
    protocol: tcp
    dport: "80"

- name: Delete a rules set
  pidginhost.cloud.firewall:
    state: absent
    name: web
"""

RETURN = r"""
firewall:
  description:
    - Rules set with its rules after the changes. After deletion, the rules set before deletion.
    - Empty when O(state=absent) and the rules set did not exist.
  returned: success
  type: dict
  sample:
    id: 12
    name: web
    status: validated
    read_only: false
    rules:
      - id: 101
        direction: in
        action: ACCEPT
        protocol: tcp
        source: ""
        sport: ""
        destination: ""
        dport: "22"
        enabled: true
        position: 0
        has_error: false
        error_message: ""
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, pidginhost_argument_spec

RULES_SETS = "/api/cloud/firewall-rules-set/"
MATCH_FIELDS = ("direction", "action", "protocol", "source", "sport", "destination", "dport")
RULE_FIELDS = MATCH_FIELDS + ("enabled", "position")
DIRECTIONS = ["in", "out"]
ACTIONS = ["ACCEPT", "DROP", "REJECT"]


def identity(rule):
    return tuple("" if rule.get(k) is None else str(rule[k]) for k in MATCH_FIELDS)


def desired_rules(module):
    params = module.params
    rules = list(params["rules"] or [])
    if params["direction"]:
        legacy = dict((k, params[k]) for k in RULE_FIELDS)
        legacy["enabled"] = legacy["enabled"] is not False
        rules.append(legacy)
    for rule in rules:
        if (rule["sport"] or rule["dport"]) and not rule["protocol"]:
            module.fail_json(msg="Firewall rule %s sets a port without a protocol." % drop_none(rule))
    return rules


def plan(existing, desired, purge):
    """Return (rules to create, (rule id, changes) to patch, rules to delete)."""
    unmatched = list(existing)
    create, patch = [], []
    for rule in desired:
        match = next((r for r in unmatched if identity(r) == identity(rule)), None)
        if match is None:
            create.append(drop_none(rule))
            continue
        unmatched.remove(match)
        changes = dict(
            (k, rule[k]) for k in ("enabled", "position") if rule[k] is not None and rule[k] != match.get(k))
        if changes:
            patch.append((match["id"], changes))
    return create, patch, unmatched if purge else []


def present(api, module, rules_set, desired):
    name = module.params["name"]
    created = rules_set is None
    if created:
        if module.check_mode:
            module.exit_json(changed=True, firewall={"name": name, "rules": [drop_none(r) for r in desired]})
        rules_set = api.post(RULES_SETS, {"name": name})

    create, patch, delete = plan(rules_set.get("rules") or [], desired, module.params["purge_rules"])
    if not (created or create or patch or delete):
        module.exit_json(changed=False, firewall=rules_set)
    if module.check_mode:
        module.exit_json(changed=True, firewall=rules_set)

    rules_path = "%s%s/rules/" % (RULES_SETS, rules_set["id"])
    for rule in delete:
        api.delete("%s%s/" % (rules_path, rule["id"]))
    for rule_id, changes in patch:
        api.patch("%s%s/" % (rules_path, rule_id), changes)
    for rule in create:
        api.post(rules_path, rule)
    module.exit_json(changed=True, firewall=api.get("%s%s/" % (RULES_SETS, rules_set["id"])))


def main():
    legacy_rule = ("protocol", "source", "sport", "destination", "dport", "enabled", "position")
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            name=dict(type="str", required=True, aliases=["rules_set_name"]),
            rules=dict(
                type="list",
                elements="dict",
                options=dict(
                    direction=dict(type="str", required=True, choices=DIRECTIONS),
                    action=dict(type="str", required=True, choices=ACTIONS),
                    protocol=dict(type="str"),
                    source=dict(type="str"),
                    sport=dict(type="str"),
                    destination=dict(type="str"),
                    dport=dict(type="str"),
                    enabled=dict(type="bool", default=True),
                    position=dict(type="int"),
                ),
            ),
            purge_rules=dict(type="bool", default=False),
            direction=dict(type="str", choices=DIRECTIONS),
            action=dict(type="str", choices=ACTIONS),
            protocol=dict(type="str"),
            source=dict(type="str"),
            sport=dict(type="str"),
            destination=dict(type="str"),
            dport=dict(type="str"),
            enabled=dict(type="bool"),
            position=dict(type="int"),
            create_rules_set=dict(
                type="bool", removed_in_version="1.0.0", removed_from_collection="pidginhost.cloud"),
        ),
        required_together=[("direction", "action")],
        required_by=dict((k, "direction") for k in legacy_rule),
        supports_check_mode=True,
    )
    desired = desired_rules(module)
    api = PidginHostAPI(module)
    rules_set = api.find_one(api.list(RULES_SETS), "firewall rules sets", name=module.params["name"])

    if module.params["state"] == "present":
        present(api, module, rules_set, desired)
    if not rules_set:
        module.exit_json(changed=False, firewall={})
    if not module.check_mode:
        api.delete("%s%s/" % (RULES_SETS, rules_set["id"]))
    module.exit_json(changed=True, firewall=rules_set)


if __name__ == "__main__":
    main()
