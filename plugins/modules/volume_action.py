# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volume_action

short_description: Attach or detach a storage volume.

version_added: 0.2.0

description:
  - Attach a storage volume to a server, or detach it from that server.
  - A volume is attached to at most one server. Detach it before attaching it to another server.
  - Detaching is asynchronous. The volume keeps its server link until the detach completes.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_attach_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - V(present) attaches the volume to the server. V(absent) detaches it from the server.
    type: str
    choices: [present, absent]
    default: present
  volume_alias:
    description:
      - Alias of the volume. Must be unique in the account.
    type: str
    required: true
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
  server_id:
    description:
      - ID of the server. Use instead of O(server_hostname).
    type: int
"""

EXAMPLES = r"""
- name: Attach a volume to a server
  pidginhost.cloud.volume_action:
    volume_alias: data
    server_hostname: web1.example.com

- name: Detach a volume from a server
  pidginhost.cloud.volume_action:
    state: absent
    volume_alias: data
    server_id: 12345
"""

RETURN = r"""
action:
  description:
    - Volume details after the action.
  returned: success
  type: dict
  sample:
    id: 321
    alias: data
    size: 50
    product: fast-storage
    attached: true
    server: web1.example.com
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, pidginhost_argument_spec

VOLUMES = "/api/cloud/volumes/"


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            volume_alias=dict(type="str", required=True),
            server_hostname=dict(type="str"),
            server_id=dict(type="int"),
        ),
        required_one_of=[("server_hostname", "server_id")],
        mutually_exclusive=[("server_hostname", "server_id")],
        supports_check_mode=True,
    )
    params = module.params
    api = PidginHostAPI(module)
    volume = api.find_one(api.list(VOLUMES), "volumes", alias=params["volume_alias"])
    if not volume:
        module.fail_json(msg="Volume %s not found." % params["volume_alias"])
    server = api.require_server(params["server_id"], params["server_hostname"])
    # The server detail lists its volumes by id, which is exact even when hostnames repeat.
    attached = volume["attached"] and any(v["id"] == volume["id"] for v in server.get("volumes", []))

    if params["state"] == "present":
        if attached:
            module.exit_json(changed=False, action=volume)
        if volume["server"]:
            module.fail_json(msg="Volume %s is attached to server %s. Detach it first."
                                 % (volume["alias"], volume["server"]), action=volume)
        action, body = "attach", {"vm": server["id"]}
    else:
        if not attached:
            module.exit_json(changed=False, action=volume)
        action, body = "detach", None

    if module.check_mode:
        module.exit_json(changed=True, action=volume)
    path = "%s%s/" % (VOLUMES, volume["id"])
    api.post(path + action + "/", body)
    module.exit_json(changed=True, action=api.get(path))


if __name__ == "__main__":
    main()
