# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: volume

short_description: Create, resize or delete storage volumes.

version_added: 0.2.0

description:
  - Create, resize or delete PidginHost storage volumes.
  - The volume is identified by its O(volume_alias), so the alias must be unique in the account.
  - A new volume is created on, and attached to, the server given by O(server_id) or O(hostname).
  - An existing volume can grow with O(size_gigabytes) and move to another O(project). Volumes cannot shrink.
  - Use M(pidginhost.cloud.volume_action) to attach or detach an existing volume.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_volumes_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the volume should exist.
      - With V(absent), an attached volume is not deleted. Detach it first with M(pidginhost.cloud.volume_action).
    type: str
    choices: [present, absent]
    default: present
  volume_alias:
    description:
      - Volume alias. Identifies the volume, so it must be unique in the account.
    type: str
    required: true
  hostname:
    description:
      - Hostname of the server to create the volume on. Must be unique in the account.
      - Only used on creation.
    type: str
  server_id:
    description:
      - ID of the server to create the volume on. Use instead of O(hostname).
      - Only used on creation.
    type: int
  size_gigabytes:
    description:
      - Volume size in GB. Required to create a volume.
      - A larger value grows an existing volume. A smaller value fails.
    type: int
  product:
    description:
      - Storage product ID or slug. Required to create a volume. See M(pidginhost.cloud.volumes_products_info).
      - Only used on creation.
    type: str
  project:
    description:
      - Project name.
    type: str
"""

EXAMPLES = r"""
- name: Create a 50 GB volume on a server
  pidginhost.cloud.volume:
    volume_alias: data
    hostname: web1.example.com
    product: fast-storage
    size_gigabytes: 50

- name: Grow the volume to 100 GB
  pidginhost.cloud.volume:
    volume_alias: data
    size_gigabytes: 100

- name: Delete a detached volume
  pidginhost.cloud.volume:
    state: absent
    volume_alias: data
"""

RETURN = r"""
volume:
  description:
    - Volume details. After deletion, the details before deletion. Empty when the volume does not exist.
  returned: success
  type: dict
  sample:
    id: 321
    alias: data
    project: ""
    size: 50
    product: fast-storage
    attached: true
    server: web1.example.com
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, pidginhost_argument_spec

VOLUMES = "/api/cloud/volumes/"


def create(api, module):
    params = module.params
    missing = [name for name in ("product", "size_gigabytes") if params[name] is None]
    if not (params["server_id"] or params["hostname"]):
        missing.insert(0, "hostname or server_id")
    if missing:
        module.fail_json(msg="Creating a volume requires: %s" % ", ".join(missing))
    server = api.require_server(params["server_id"], params["hostname"])
    if module.check_mode:
        module.exit_json(changed=True, volume={})

    body = drop_none(dict(alias=params["volume_alias"], size=params["size_gigabytes"], product=params["product"],
                          project=params["project"]))
    module.exit_json(changed=True, volume=api.post("%s%s/volumes/" % (SERVERS, server["id"]), body))


def update(api, module, volume):
    params = module.params
    size = params["size_gigabytes"]
    if size is not None and size < volume["size"]:
        module.fail_json(msg="Volume %s is %s GB and volumes cannot shrink to %s GB."
                             % (volume["alias"], volume["size"], size), volume=volume)
    body = {}
    if size is not None and size > volume["size"]:
        body["size"] = size
    if params["project"] is not None and params["project"] != volume["project"]:
        body["project"] = params["project"]
    if not body:
        module.exit_json(changed=False, volume=volume)
    if module.check_mode:
        module.exit_json(changed=True, volume=dict(volume, **body))
    module.exit_json(changed=True, volume=api.patch("%s%s/" % (VOLUMES, volume["id"]), body))


def delete(api, module, volume):
    if volume["server"]:
        module.fail_json(msg="Volume %s is attached to server %s. Detach it first with pidginhost.cloud.volume_action."
                             % (volume["alias"], volume["server"]), volume=volume)
    if not module.check_mode:
        api.delete("%s%s/" % (VOLUMES, volume["id"]))
    module.exit_json(changed=True, volume=volume)


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            volume_alias=dict(type="str", required=True),
            hostname=dict(type="str"),
            server_id=dict(type="int"),
            size_gigabytes=dict(type="int"),
            product=dict(type="str"),
            project=dict(type="str"),
        ),
        mutually_exclusive=[("hostname", "server_id")],
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    volume = api.find_one(api.list(VOLUMES), "volumes", alias=module.params["volume_alias"])

    if module.params["state"] == "absent":
        if not volume:
            module.exit_json(changed=False, volume={})
        delete(api, module, volume)
    elif volume:
        update(api, module, volume)
    else:
        create(api, module)


if __name__ == "__main__":
    main()
