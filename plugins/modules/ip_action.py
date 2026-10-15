# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ip_action

short_description: Attach or detach a public IP address.

version_added: 0.2.0

description:
  - Attach a public IPv4 or IPv6 address you own to a server, or detach it.
  - The guest OS only picks up a newly attached address when it boots. Set O(reboot=true) to restart the server on
    attach.
  - Use M(pidginhost.cloud.ip) to allocate or release addresses.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_attach_ipv4_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - V(present) attaches the address to the server. V(absent) detaches it.
    type: str
    choices: [present, absent]
    default: present
  ip_address:
    description:
      - IPv4 or IPv6 address in your account.
    type: str
    required: true
  server_id:
    description:
      - ID of the server. Takes precedence over O(server_hostname).
      - One of O(server_id) or O(server_hostname) is required with O(state=present).
      - With O(state=absent), the address is only detached when it is attached to this server.
    type: int
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
  reboot:
    description:
      - Restart the server after attaching the address so the guest OS picks it up.
    type: bool
    default: false
  server_ip:
    description:
      - Ignored.
    type: str
"""

EXAMPLES = r"""
- name: Attach an IP address and restart the server
  pidginhost.cloud.ip_action:
    ip_address: 192.0.2.10
    server_hostname: web1.example.com
    reboot: true

- name: Attach an IPv6 address by server id
  pidginhost.cloud.ip_action:
    ip_address: 2001:db8::10
    server_id: 12345

- name: Detach an IP address from whatever server holds it
  pidginhost.cloud.ip_action:
    state: absent
    ip_address: 192.0.2.10
"""

RETURN = r"""
ip_result:
  description: API response of the attach or detach call. Empty when nothing changed or in check mode.
  returned: success
  type: dict
  sample:
    attached: true
    reboot_required: false
    rebooted: true
ip:
  description: The IP address, as it is after the change.
  returned: success
  type: dict
  sample:
    id: 7
    address: 192.0.2.10
    gateway: 192.0.2.1
    prefix: 24
    attached: true
    server: web1.example.com
    server_id: 12345
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            ip_address=dict(type="str", required=True),
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            reboot=dict(type="bool", default=False),
            server_ip=dict(type="str", removed_in_version="1.0.0", removed_from_collection="pidginhost.cloud"),
        ),
        required_if=[("state", "present", ("server_id", "server_hostname"), True)],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    version, ip = api.find_ip(params["ip_address"])
    if not ip:
        module.fail_json(msg="IP address %s is not in your account." % params["ip_address"])

    # "attached" flips only once the network change is applied; server_id already names the server before that.
    bound = ip["attached"] or ip["server_id"] is not None
    if params["state"] == "present":
        server = api.require_server(params["server_id"], params["server_hostname"])
        if bound:
            if ip["server_id"] != server["id"]:
                module.fail_json(msg="IP address %s is attached to another server (%s); detach it first."
                                     % (ip["address"], ip["server"] or ip["server_id"]), ip=ip)
            module.exit_json(changed=False, ip_result={}, ip=ip)
        if module.check_mode:
            module.exit_json(changed=True, ip_result={}, ip=ip)
        result = api.post("%s%s/attach-ipv%d/" % (SERVERS, server["id"], version),
                          {"ipv%d" % version: ip["address"], "reboot": params["reboot"]})
    else:
        if not bound:
            module.exit_json(changed=False, ip_result={}, ip=ip)
        target_id = params["server_id"]
        if target_id is None and params["server_hostname"]:
            target = api.find_server(hostname=params["server_hostname"])
            if not target:
                module.exit_json(changed=False, ip_result={}, ip=ip)
            target_id = target["id"]
        if target_id is not None and target_id != ip["server_id"]:
            module.exit_json(changed=False, ip_result={}, ip=ip)
        if module.check_mode:
            module.exit_json(changed=True, ip_result={}, ip=ip)
        result = api.post("/api/cloud/ipv%d/%s/detach/" % (version, ip["id"]))

    module.exit_json(changed=True, ip_result=result, ip=api.get("/api/cloud/ipv%d/%s/" % (version, ip["id"])))


if __name__ == "__main__":
    main()
