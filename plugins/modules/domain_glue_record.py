# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: domain_glue_record

short_description: Manage a child nameserver host of a registered domain.

version_added: 0.4.0

description:
  - Register or delete a glue record at the registry. It makes O(name).O(domain) a nameserver host with the
    addresses O(ip) and O(ip2), so domains can delegate to it.
  - The domain must be registered with PidginHost and its service must be active or pending cancellation.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/domain/domain_domain_dns_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the glue record should exist.
    type: str
    choices: [present, absent]
    default: present
  domain:
    description:
      - Domain name, for example V(example.com).
    type: str
    required: true
  name:
    description:
      - Nameserver label, for example V(ns1) for C(ns1.example.com).
    type: str
    required: true
  ip:
    description:
      - IP address of the nameserver host. Required with O(state=present).
    type: str
  ip2:
    description:
      - Second IP address of the nameserver host.
      - When not set, the glue record has no second address.
    type: str
"""

EXAMPLES = r"""
- name: Register ns1.example.com at the registry
  pidginhost.cloud.domain_glue_record:
    domain: example.com
    name: ns1
    ip: 192.0.2.53
    ip2: 2001:db8::53

- name: Delete the glue record
  pidginhost.cloud.domain_glue_record:
    domain: example.com
    name: ns1
    state: absent
"""

RETURN = r"""
glue_record:
  description:
    - The glue record. After deletion, the record before deletion.
    - Empty when O(state=absent) and the record did not exist.
  returned: success
  type: dict
  sample:
    name: ns1
    ip: 192.0.2.53
    ip2: 2001:db8::53
"""

import ipaddress

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, fqdn, pidginhost_argument_spec


def address(value):
    if not value:
        return ""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return value


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            domain=dict(type="str", required=True),
            name=dict(type="str", required=True),
            ip=dict(type="str"),
            ip2=dict(type="str"),
        ),
        required_if=[("state", "present", ["ip"])],
        supports_check_mode=True,
    )
    params = module.params
    path = "/api/domain/domain/%s/dns/" % fqdn(params["domain"])
    api = PidginHostAPI(module, sensitive=True)
    record = next((r for r in api.list(path) if r["name"].lower() == params["name"].lower()), None)

    if params["state"] == "absent":
        if not record:
            module.exit_json(changed=False, glue_record={})
        if not module.check_mode:
            api.delete("%s%s/" % (path, record["name"]))
        module.exit_json(changed=True, glue_record=record)

    wanted = (address(params["ip"]), address(params["ip2"]))
    if record and (address(record["ip"]), address(record.get("ip2"))) == wanted:
        module.exit_json(changed=False, glue_record=record)
    # The API upserts by name: keep the stored spelling so it updates instead of adding a second host.
    body = drop_none({"name": record["name"] if record else params["name"], "ip": params["ip"], "ip2": params["ip2"]})
    if module.check_mode:
        module.exit_json(changed=True, glue_record=body)
    module.exit_json(changed=True, glue_record=api.post(path, body))


if __name__ == "__main__":
    main()
