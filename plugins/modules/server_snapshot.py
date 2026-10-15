# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_snapshot

short_description: Create, delete or roll back cloud server snapshots.

version_added: 0.4.0

description:
  - Create or delete a snapshot of a PidginHost cloud server, or roll the server back to one.
  - The server is identified by O(server_id) or by its unique O(server_hostname).
  - The snapshot is identified by O(name). An existing snapshot is never changed.
  - The API only accepts snapshot requests while the server status is C(active), and not while it boots from an ISO.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/cloud/cloud_servers_snapshots_create).

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
  name:
    description:
      - Snapshot name. Starts with a letter, then 1 to 39 letters, digits, C(_) or C(-).
    type: str
    required: true
  description:
    description:
      - Snapshot description. Only used on creation.
    type: str
  include_memory:
    description:
      - Also save the memory of a running server. Only used on creation.
    type: bool
  state:
    description:
      - V(present) creates the snapshot when it does not exist.
      - V(absent) deletes the snapshot when it exists.
      - V(rollback) rolls the server back to the snapshot, which must exist. This always reports a change.
    type: str
    choices: [present, absent, rollback]
    default: present
  wait:
    description:
      - Wait until the snapshot is ready after creation, or gone after deletion.
      - With O(state=rollback), wait until the server status is C(active).
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Snapshot a server before an upgrade
  pidginhost.cloud.server_snapshot:
    server_hostname: web1.example.com
    name: before-upgrade
    description: Before the OS upgrade

- name: Roll back to the snapshot
  pidginhost.cloud.server_snapshot:
    server_hostname: web1.example.com
    name: before-upgrade
    state: rollback

- name: Delete the snapshot
  pidginhost.cloud.server_snapshot:
    server_id: 12345
    name: before-upgrade
    state: absent
"""

RETURN = r"""
snapshot:
  description:
    - Snapshot details. Empty with O(state=absent), and in check mode when the snapshot would be created.
    - After creation with O(wait=false), only the name.
  returned: success
  type: dict
  sample:
    name: before-upgrade
    description: Before the OS upgrade
    state: ""
    created_at: "2026-01-01T10:00:00Z"
    includes_memory: false
    is_current: false
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import SERVERS, PidginHostAPI, drop_none, pidginhost_argument_spec


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            server_id=dict(type="int"),
            server_hostname=dict(type="str"),
            name=dict(type="str", required=True),
            description=dict(type="str"),
            include_memory=dict(type="bool"),
            state=dict(type="str", choices=["present", "absent", "rollback"], default="present"),
            wait=dict(type="bool", default=True),
        ),
        required_one_of=[("server_id", "server_hostname")],
        supports_check_mode=True,
    )
    params = module.params
    name = params["name"]
    state = params["state"]
    api = PidginHostAPI(module)
    server = api.require_server(params["server_id"], params["server_hostname"])
    server_path = "%s%s/" % (SERVERS, server["id"])
    path = server_path + "snapshots/"

    def find():
        return api.find_one(api.list(path), "snapshots", name=name)

    snapshot = find()

    if state == "present":
        if snapshot:
            module.exit_json(changed=False, snapshot=snapshot)
        if module.check_mode:
            module.exit_json(changed=True, snapshot={})
        api.post(path, drop_none(dict(
            name=name, description=params["description"], include_memory=params["include_memory"])))
        if not params["wait"]:
            module.exit_json(changed=True, snapshot={"name": name})
        # The snapshot is listed with state "prepare" until it is complete.
        snapshot = api.wait_for(find, lambda s: s is not None and s["state"] != "prepare")
        if not snapshot:
            module.fail_json(changed=True, msg="Snapshot %s was not ready in time." % name, snapshot={"name": name})
        module.exit_json(changed=True, snapshot=snapshot)

    if state == "absent":
        if not snapshot:
            module.exit_json(changed=False, snapshot={})
        if module.check_mode:
            module.exit_json(changed=True, snapshot={})
        api.delete("%s%s/" % (path, name))
        if params["wait"] and not api.wait_for(lambda: find() is None, bool):
            module.fail_json(changed=True, msg="Snapshot %s was not deleted in time." % name, snapshot=snapshot)
        module.exit_json(changed=True, snapshot={})

    if not snapshot:
        module.fail_json(msg="Snapshot %s not found on server %s." % (name, server["id"]))
    if module.check_mode:
        module.exit_json(changed=True, snapshot=snapshot)
    api.post("%s%s/rollback/" % (path, name))
    if params["wait"] and not api.wait_for(lambda: api.get(server_path), lambda s: s["status"] == "active"):
        module.fail_json(
            changed=True, msg="Server %s did not become active in time after the rollback." % server["id"],
            snapshot=snapshot,
        )
    module.exit_json(changed=True, snapshot=snapshot)


if __name__ == "__main__":
    main()
