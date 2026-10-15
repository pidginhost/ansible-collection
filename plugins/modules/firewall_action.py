# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewall_action

short_description: Apply a firewall rules set and default policies to a server.

version_added: 0.2.0

description:
  - Set the firewall rules set and the default policies of the public interface of a server.
  - Options that are not set keep their current value. Nothing is sent when every given value already matches.
  - Use M(pidginhost.cloud.firewall) to manage the rules set itself.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_public_interface_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Only V(present) is supported.
    type: str
    choices: [present]
    default: present
  server_id:
    description:
      - ID of the server.
    type: int
  server_hostname:
    description:
      - Server hostname. Used when O(server_id) is not set, so it must be unique in the account.
    type: str
  rules_set_name:
    description:
      - Name of the firewall rules set to apply.
    type: str
  policy_in:
    description:
      - Default policy for incoming traffic.
    type: str
    choices: [ACCEPT, DROP, REJECT]
  policy_out:
    description:
      - Default policy for outgoing traffic.
    type: str
    choices: [ACCEPT, DROP, REJECT]
"""

EXAMPLES = r"""
- name: Apply a rules set and drop other incoming traffic
  pidginhost.cloud.firewall_action:
    server_hostname: web1.example.com
    rules_set_name: web
    policy_in: DROP
    policy_out: ACCEPT

- name: Change only the incoming policy
  pidginhost.cloud.firewall_action:
    server_id: 12345
    policy_in: ACCEPT
"""

RETURN = r"""
firewall:
  description:
    - Public interface of the server after the change.
  returned: success
  type: dict
  sample:
    interface: net0
    ipv4: 192.0.2.10
    ipv6: 2001:db8::10
    fw_rules_set: web
    fw_policy_in: DROP
    fw_policy_out: ACCEPT
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, pidginhost_argument_spec

POLICIES = ["ACCEPT", "DROP", "REJECT"]


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present"], default="present"),
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            rules_set_name=dict(type="str"),
            policy_in=dict(type="str", choices=POLICIES),
            policy_out=dict(type="str", choices=POLICIES),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    server = api.require_server(params["server_id"], params["server_hostname"])
    path = "%s%s/public-interface/" % (SERVERS, server["id"])
    current = api.get(path)

    wanted = drop_none(dict(
        fw_rules_set=params["rules_set_name"], fw_policy_in=params["policy_in"], fw_policy_out=params["policy_out"]))
    if all(current.get(k) == v for k, v in wanted.items()):
        module.exit_json(changed=False, firewall=current)
    merged = dict(current, **wanted)
    if module.check_mode:
        module.exit_json(changed=True, firewall=merged)
    body = dict((k, merged.get(k)) for k in ("fw_rules_set", "fw_policy_in", "fw_policy_out"))
    applied = api.post(path, body)
    kept = dict((k, applied.get(k)) for k, v in wanted.items() if applied.get(k) != v)
    if kept:
        # Some packages, such as the free tier, lock the firewall: the API answers but keeps its own values.
        module.fail_json(
            changed=any(applied.get(k) != current.get(k) for k in body), firewall=applied,
            msg="The firewall of server %s is locked; the API kept %s." % (server["id"], kept))
    module.exit_json(changed=True, firewall=applied)


if __name__ == "__main__":
    main()
