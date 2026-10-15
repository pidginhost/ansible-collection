# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_action_resize

short_description: Change the package of a cloud server or grow one of its volumes.

version_added: 0.2.0

description:
  - With O(disk=false), move a PidginHost cloud server to another package.
    The API refuses packages with a smaller disk and checks the account funds.
  - With O(disk=true), grow a volume attached to the server. Volumes cannot shrink.
  - The server is identified by O(server_id) or by its unique O(server_hostname).
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_modify_package_create)
    and U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_volumes_partial_update).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost
  - pidginhost.cloud.pidginhost.info

options:
  server_id:
    description:
      - ID of the server. Takes precedence over O(server_hostname).
    type: int
  server_hostname:
    description:
      - Hostname of the server. Must be unique in the account.
    type: str
  disk:
    description:
      - V(false) changes the server package to O(package_name).
      - V(true) grows the volume O(volume_alias) to O(size_gigabytes).
    type: bool
    default: false
  package_name:
    description:
      - Package slug to move the server to. Required when O(disk=false). See M(pidginhost.cloud.packages_info).
      - Nothing is done when the server already uses this package. Use the slug, not the ID, to keep this check working.
    type: str
    aliases: [package]
  volume_alias:
    description:
      - Alias of the server volume to grow. Required when O(disk=true).
    type: str
  size_gigabytes:
    description:
      - New volume size in GB. Required when O(disk=true). Must not be smaller than the current size.
    type: int
  project:
    description:
      - Project name to set on the volume when it is resized.
    type: str
  wait:
    description:
      - Wait until the server is C(active) again after a package change.
    type: bool
    default: true
  product:
    description:
      - Ignored. The storage product of a volume cannot change.
    type: str
"""

EXAMPLES = r"""
- name: Move a server to a bigger package
  pidginhost.cloud.server_action_resize:
    server_hostname: web1.example.com
    package: cloudv-3

- name: Grow a server volume to 60 GB
  pidginhost.cloud.server_action_resize:
    server_id: 12345
    disk: true
    volume_alias: data
    size_gigabytes: 60
"""

RETURN = r"""
action:
  description:
    - With O(disk=false), the server details. After a change with O(wait=false), the details before the change.
    - With O(disk=true), the volume details.
  returned: success
  type: dict
  sample:
    id: 12345
    hostname: web1.example.com
    status: active
    package: cloudv-3
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, info_argument_spec


def change_package(api, module, server):
    package = module.params["package_name"]
    if server["package"] == package:
        module.exit_json(changed=False, action=server)
    if module.check_mode:
        module.exit_json(changed=True, action=server)

    path = "%s%s/" % (SERVERS, server["id"])
    api.post(path + "modify-package/", {"package": package})
    if not module.params["wait"]:
        module.exit_json(changed=True, action=server)
    # The server goes through upgrading and back to active.
    done = api.wait_for(lambda: api.get(path), lambda s: s["status"] == "active")
    if not done:
        module.fail_json(
            changed=True, msg="Server %s did not become active in time after the package change." % server["id"],
            action=server,
        )
    module.exit_json(changed=True, action=done)


def grow_volume(api, module, server):
    params = module.params
    volume = api.find_one(server["volumes"], "volumes", alias=params["volume_alias"])
    if not volume:
        module.fail_json(msg="Volume %s not found on server %s." % (params["volume_alias"], server["id"]))
    size = params["size_gigabytes"]
    if size < volume["size"]:
        module.fail_json(msg="Volume %s is %s GB and cannot shrink to %s GB." % (volume["alias"], volume["size"], size))
    if size == volume["size"]:
        module.exit_json(changed=False, action=volume)
    if module.check_mode:
        module.exit_json(changed=True, action=volume)
    volume = api.patch("/api/cloud/volumes/%s/" % volume["id"], drop_none(dict(size=size, project=params["project"])))
    module.exit_json(changed=True, action=volume)


def main():
    module = AnsibleModule(
        argument_spec=info_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            disk=dict(type="bool", default=False),
            package_name=dict(type="str", aliases=["package"]),
            volume_alias=dict(type="str"),
            size_gigabytes=dict(type="int"),
            project=dict(type="str"),
            wait=dict(type="bool", default=True),
            product=dict(type="str", removed_in_version="1.0.0", removed_from_collection="pidginhost.cloud"),
        ),
        required_one_of=[("server_id", "server_hostname")],
        required_if=[
            ("disk", False, ["package_name"]),
            ("disk", True, ["volume_alias", "size_gigabytes"]),
        ],
        supports_check_mode=True,
    )
    api = PidginHostAPI(module)
    server = api.require_server(module.params["server_id"], module.params["server_hostname"])
    if module.params["disk"]:
        grow_volume(api, module, server)
    change_package(api, module, server)


if __name__ == "__main__":
    main()
