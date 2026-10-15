# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ip

short_description: Allocate or release public IP addresses and set their reverse DNS.

version_added: 0.4.0

description:
  - Allocate a new public IPv4 or IPv6 address, release one you own, or set its reverse DNS (PTR) name.
  - Allocating with O(state=present) and no O(address) is not idempotent. Every run allocates a new address.
    Register the result and pass its address on later runs.
  - Use M(pidginhost.cloud.ip_action) to attach an address to a server.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_ipv4_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - V(present) allocates a new address when O(address) is not set, or manages the existing O(address).
      - V(absent) releases O(address).
    type: str
    choices: [present, absent]
    default: present
  address:
    description:
      - IPv4 or IPv6 address in your account.
      - Required with O(state=absent).
    type: str
  version:
    description:
      - IP version of the address to allocate. Required when O(address) is not set.
      - Ignored when O(address) is set.
    type: int
    choices: [4, 6]
  reverse_dns:
    description:
      - Fully qualified domain name for the PTR record of the address.
    type: str
"""

EXAMPLES = r"""
- name: Allocate a new IPv4 address
  pidginhost.cloud.ip:
    version: 4
    reverse_dns: web1.example.com
  register: new_ip

- name: Set reverse DNS of an address you own
  pidginhost.cloud.ip:
    address: 192.0.2.10
    reverse_dns: web1.example.com

- name: Release an address
  pidginhost.cloud.ip:
    state: absent
    address: 2001:db8::10
"""

RETURN = r"""
ip:
  description:
    - The IP address. After release, the details before release.
    - Contains C(reverse_dns) when O(reverse_dns) is set.
    - Empty when the address to release was not found, or when allocating in check mode.
  returned: success
  type: dict
  sample:
    id: 7
    address: 192.0.2.10
    gateway: 192.0.2.1
    prefix: 24
    attached: false
    server: ""
    server_id: null
    reverse_dns: web1.example.com
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            address=dict(type="str"),
            version=dict(type="int", choices=[4, 6]),
            reverse_dns=dict(type="str"),
        ),
        required_one_of=[("address", "version")],
        required_if=[("state", "absent", ["address"])],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)

    if not params["address"]:
        if module.check_mode:
            module.exit_json(changed=True, ip={})
        base = "/api/cloud/ipv%d/" % params["version"]
        ip = api.post(base)
        if params["reverse_dns"]:
            ip.update(api.post("%s%s/rdns/" % (base, ip["id"]), {"reverse_dns": params["reverse_dns"]}))
        module.exit_json(changed=True, ip=ip)

    version, ip = api.find_ip(params["address"])
    if params["state"] == "absent":
        if not ip:
            module.exit_json(changed=False, ip={})
        if not module.check_mode:
            api.delete("/api/cloud/ipv%d/%s/" % (version, ip["id"]))
        module.exit_json(changed=True, ip=ip)

    if not ip:
        module.fail_json(msg="IP address %s is not in your account." % params["address"])
    changed = False
    if params["reverse_dns"] is not None:
        rdns_path = "/api/cloud/ipv%d/%s/rdns/" % (version, ip["id"])
        ip.update(api.get(rdns_path))
        if ip["reverse_dns"] != params["reverse_dns"]:
            changed = True
            if not module.check_mode:
                ip.update(api.post(rdns_path, {"reverse_dns": params["reverse_dns"]}))
    module.exit_json(changed=changed, ip=ip)


if __name__ == "__main__":
    main()
