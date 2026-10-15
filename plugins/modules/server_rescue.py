# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_rescue

short_description: Boot cloud servers into rescue mode or back out of it.

version_added: 0.4.0

description:
  - Boot a PidginHost cloud server from the rescue image or a catalog ISO, or return it to a normal boot.
  - Entering rescue mode powers the server off first. Use the console to repair or install the server.
  - The server is identified by O(server_id) or by its unique O(server_hostname).
  - Only the C(rescue_mode) flag of the server is compared. A server already in rescue mode is left alone, whatever
    ISO it booted.
  - Rescue mode is not available for servers with high availability enabled.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_rescue_enter_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  server_id:
    description:
      - ID of the server. Takes precedence over O(server_hostname).
    type: int
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
  state:
    description:
      - V(present) boots the server in rescue mode.
      - V(absent) leaves rescue mode and boots the server normally.
    type: str
    choices: [present, absent]
    default: present
  iso:
    description:
      - Catalog ISO slug to boot instead of the default rescue image. Only used with O(state=present).
      - To list the ISOs a server can boot, add V(boot_isos) to the C(include) option of
        M(pidginhost.cloud.servers_info).
    type: str
  wait:
    description:
      - Wait until the server reports the requested rescue mode.
      - The API queues the change and accepts it before it runs. When the server activity log reports that it
        could not run because another operation held the server, the change is sent again until it runs or
        O(timeout) passes. Any other refusal fails the task at once with its message.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Boot a server in rescue mode
  pidginhost.cloud.server_rescue:
    server_hostname: web1.example.com

- name: Boot an installer ISO
  pidginhost.cloud.server_rescue:
    server_id: 12345
    iso: debian-13-netinst

- name: Boot the server normally again
  pidginhost.cloud.server_rescue:
    server_hostname: web1.example.com
    state: absent
"""

RETURN = r"""
server:
  description:
    - Server details. After a change with O(wait=false), the details before the change.
  returned: success
  type: dict
  sample:
    id: 12345
    hostname: web1.example.com
    status: active
    rescue_mode: true
    boot_iso: null
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            iso=dict(type="str"),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    server = api.require_server(params["server_id"], params["server_hostname"])
    path = "%s%s/" % (SERVERS, server["id"])
    rescue = params["state"] == "present"

    if server["rescue_mode"] == rescue:
        module.exit_json(changed=False, server=server)
    if module.check_mode:
        module.exit_json(changed=True, server=server)

    before = api.activity(server["id"]) if params["wait"] else None
    if rescue:
        refusals = ("Could not boot from ISO", "Could not enter rescue mode")

        def submit():
            api.post(path + "rescue/enter/", drop_none(dict(iso=params["iso"])))
    else:
        refusals = ("Could not exit ISO boot", "Could not exit rescue mode")

        def submit():
            api.post(path + "rescue/exit/")
    submit()
    if not params["wait"]:
        module.exit_json(changed=True, server=server)

    def settled(fresh):
        current = api.get(path)
        return current if current["rescue_mode"] == rescue else None

    done = api.wait_activity(
        server["id"], before, refusals, settled,
        "%s rescue mode on server %s" % ("Entering" if rescue else "Leaving", server["id"]),
        resubmit=submit, server=server)
    module.exit_json(changed=True, server=done)


if __name__ == "__main__":
    main()
