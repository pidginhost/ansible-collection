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
      - Also wait for an earlier creation or deletion that is still in progress.
      - With O(state=rollback), wait for a new completion entry in the server activity log.
      - The API queues snapshot work and accepts it before it runs. When the server activity log reports that it
        could not run because another operation held the server, the request is sent again until it runs or
        O(timeout) passes. Any other refusal or failure fails the task at once with its message.
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


def wait_ready(api, module, find, changed):
    snapshot = api.wait_for(find, lambda s: s is not None and s["state"] == "")
    if snapshot is None:
        module.fail_json(changed=changed, msg="Snapshot %s was not ready in time." % module.params["name"],
                         snapshot={"name": module.params["name"]})
    return snapshot


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
            if snapshot["state"] and params["wait"] and not module.check_mode:
                snapshot = wait_ready(api, module, find, changed=False)
            module.exit_json(changed=False, snapshot=snapshot)
        if module.check_mode:
            module.exit_json(changed=True, snapshot={})
        before = api.activity(server["id"]) if params["wait"] else None

        def create():
            api.post(path, drop_none(dict(
                name=name, description=params["description"], include_memory=params["include_memory"])))

        create()
        if not params["wait"]:
            module.exit_json(changed=True, snapshot={"name": name})

        def ready(fresh):
            # The snapshot is listed with a state until it is complete.
            found = find()
            return found if found and found["state"] == "" else None

        prefix = 'Snapshot "%s" ' % name
        snapshot = api.wait_activity(
            server["id"], before, (prefix + "could not be created", prefix + "was not created"), ready,
            "Snapshot %s" % name, resubmit=create, snapshot={"name": name})
        module.exit_json(changed=True, snapshot=snapshot)

    if state == "absent":
        if not snapshot:
            module.exit_json(changed=False, snapshot={})
        changed = snapshot["state"] != "delete"
        if module.check_mode:
            module.exit_json(changed=changed, snapshot={})
        if not params["wait"]:
            if changed:
                api.delete("%s%s/" % (path, name))
            module.exit_json(changed=changed, snapshot={})
        if not changed:
            # A deletion already in progress: only wait for it.
            if not api.wait_for(lambda: find() is None, bool):
                module.fail_json(changed=False, msg="Snapshot %s was not deleted in time." % name, snapshot=snapshot)
            module.exit_json(changed=False, snapshot={})
        before = api.activity(server["id"])

        def delete():
            api.delete("%s%s/" % (path, name))

        delete()
        prefix = 'Snapshot "%s" ' % name
        api.wait_activity(
            server["id"], before, (prefix + "could not be deleted", prefix + "was not deleted"),
            lambda fresh: True if find() is None else None, "Snapshot %s" % name, resubmit=delete, snapshot=snapshot)
        module.exit_json(changed=True, snapshot={})

    if not snapshot:
        module.fail_json(msg="Snapshot %s not found on server %s." % (name, server["id"]))
    if module.check_mode:
        module.exit_json(changed=True, snapshot=snapshot)
    before = api.activity(server["id"]) if params["wait"] else None

    def rollback():
        api.post("%s%s/rollback/" % (path, name))

    rollback()
    if params["wait"]:
        prefix = 'Rollback to snapshot "%s" ' % name
        # The server remains active while the rollback is queued and running, so only the log tells.
        api.wait_activity(server["id"], before, (prefix + "could not be completed", prefix + "was not started"),
                          lambda fresh: True if any(m.startswith((prefix + "completed.", prefix + "completed ("))
                                                    for m in fresh) else None,
                          "Rollback to snapshot %s" % name, resubmit=rollback, snapshot=snapshot)
    module.exit_json(changed=True, snapshot=snapshot)


if __name__ == "__main__":
    main()
