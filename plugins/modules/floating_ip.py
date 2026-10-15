# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: floating_ip

short_description: Manage floating IP addresses.

version_added: 0.4.0

description:
  - Create or delete floating IPv4 and IPv6 addresses, set their reverse DNS and choose the servers allowed to use them.
  - A floating IP can be authorized on several servers at once. The servers claim it from inside the guest, for
    example with keepalived.
  - The floating IP is found by O(floating_ip_id), O(address) or O(label), in that order. Only O(label) can create a
    new one.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_floating_ipv4_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the floating IP should exist.
    type: str
    choices: [present, absent]
    default: present
  version:
    description:
      - IP version of the floating IP.
      - Ignored when O(address) is set.
    type: int
    choices: [4, 6]
    default: 4
  label:
    description:
      - Label of the floating IP. Must be unique in the account.
      - Used to find the floating IP when O(floating_ip_id) and O(address) are not set, and set when it is created.
    type: str
  floating_ip_id:
    description:
      - ID of an existing floating IP.
    type: int
  address:
    description:
      - Address of an existing floating IP.
    type: str
  reverse_dns:
    description:
      - Fully qualified domain name for the PTR record of the address.
    type: str
  authorized_servers:
    description:
      - IDs or hostnames of the servers allowed to use the floating IP.
      - When set, this is the exact list. Missing servers are authorized and the others are removed.
      - Hostnames must be unique in the account.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Create a floating IP shared by two servers
  pidginhost.cloud.floating_ip:
    label: web-vip
    reverse_dns: www.example.com
    authorized_servers:
      - web1.example.com
      - web2.example.com
  register: vip

- name: Remove every authorization from a floating IPv6
  pidginhost.cloud.floating_ip:
    address: 2001:db8::5
    authorized_servers: []

- name: Delete a floating IP
  pidginhost.cloud.floating_ip:
    state: absent
    label: web-vip
"""

RETURN = r"""
floating_ip:
  description:
    - The floating IP. After deletion, the details before deletion.
    - Empty when it did not exist, or when it is created in check mode.
  returned: success
  type: dict
  contains:
    authorized_servers:
      description: IDs of the servers allowed to use the floating IP.
      returned: when O(state=present)
      type: list
      elements: int
  sample:
    id: 3
    address: 203.0.113.5
    gateway: 203.0.113.1
    prefix: 24
    reverse_dns: www.example.com
    label: web-vip
    authorized_vm_count: 2
    created_at: "2026-01-01T00:00:00Z"
    authorized_servers: [12345, 12346]
"""

import ipaddress

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, ip_version, pidginhost_argument_spec


def find_floating_ip(api, module, base):
    params = module.params
    if params["floating_ip_id"]:
        return api.get("%s%s/" % (base, params["floating_ip_id"]), allow_404=True)
    items = api.list(base)
    if params["address"]:
        wanted = ipaddress.ip_address(params["address"])
        return next((i for i in items if ipaddress.ip_address(i["address"]) == wanted), None)
    return api.find_one(items, "floating IPs", label=params["label"])


def server_ids(api, module, names):
    ids, servers = set(), None
    for name in names:
        if name.isdigit():
            ids.add(int(name))
            continue
        if servers is None:
            servers = api.list(SERVERS)
        match = api.find_one(servers, "servers", hostname=name)
        if not match:
            module.fail_json(msg="Server %s not found." % name)
        ids.add(match["id"])
    return ids


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            version=dict(type="int", choices=[4, 6], default=4),
            label=dict(type="str"),
            floating_ip_id=dict(type="int"),
            address=dict(type="str"),
            reverse_dns=dict(type="str"),
            authorized_servers=dict(type="list", elements="str"),
        ),
        required_one_of=[("label", "floating_ip_id", "address")],
        mutually_exclusive=[("floating_ip_id", "address")],
        supports_check_mode=True,
    )
    params = module.params
    version = params["version"]
    if params["address"]:
        version = ip_version(params["address"])
        if not version:
            module.fail_json(msg="%s is not a valid IP address." % params["address"])
    base = "/api/cloud/floating-ipv%d/" % version
    api = PidginHostAPI(module)
    fip = find_floating_ip(api, module, base)

    if params["state"] == "absent":
        if not fip:
            module.exit_json(changed=False, floating_ip={})
        if not module.check_mode:
            api.delete("%s%s/" % (base, fip["id"]))
        module.exit_json(changed=True, floating_ip=fip)

    changed = False
    if not fip:
        if params["floating_ip_id"] or params["address"]:
            module.fail_json(msg="Floating IP %s not found." % (params["floating_ip_id"] or params["address"]))
        if module.check_mode:
            module.exit_json(changed=True, floating_ip={})
        fip = api.post(base, {"label": params["label"]})
        changed = True
    path = "%s%s/" % (base, fip["id"])

    if params["reverse_dns"] is not None and params["reverse_dns"] != fip["reverse_dns"]:
        changed = True
        if not module.check_mode:
            api.post(path + "rdns/", {"reverse_dns": params["reverse_dns"]})

    authorized = set(a["server_id"] for a in api.list(path + "authorizations/"))
    if params["authorized_servers"] is not None:
        wanted = server_ids(api, module, params["authorized_servers"])
        for action, ids in (("authorize", wanted - authorized), ("unauthorize", authorized - wanted)):
            for server_id in sorted(ids):
                changed = True
                if not module.check_mode:
                    api.post(path + action + "/", {"server_id": server_id})
        authorized = wanted

    if changed and not module.check_mode:
        fip = api.get(path)
    fip["authorized_servers"] = sorted(authorized)
    module.exit_json(changed=changed, floating_ip=fip)


if __name__ == "__main__":
    main()
