# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_key

short_description: Manage account SSH keys.

version_added: 0.2.0

description:
  - Add or remove SSH public keys of the account.
  - Keys are compared on their type and base64 data. The comment is ignored.
  - See U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_create).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  state:
    description:
      - Whether the keys should exist.
    type: str
    choices: [present, absent]
    default: present
  ssh_pub_key:
    description:
      - One SSH public key.
      - Exactly one of O(ssh_pub_key) and O(ssh_pub_keys) is required.
    type: str
  ssh_pub_keys:
    description:
      - A list of SSH public keys.
    type: list
    elements: str
  alias:
    description:
      - Alias of the keys. Updated on existing keys when it differs.
      - When not set, a new key takes its comment as alias.
    type: str
  delete_others:
    description:
      - Delete every account key that is not listed. Only valid with O(state=present).
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Add a key
  pidginhost.cloud.ssh_key:
    ssh_pub_key: "{{ lookup('ansible.builtin.file', '~/.ssh/id_ed25519.pub') }}"
    alias: laptop

- name: Keep only these keys in the account
  pidginhost.cloud.ssh_key:
    ssh_pub_keys:
      - ssh-ed25519 AAAA... alice@example.com
      - ssh-ed25519 BBBB... bob@example.com
    delete_others: true

- name: Remove a key
  pidginhost.cloud.ssh_key:
    state: absent
    ssh_pub_key: ssh-ed25519 AAAA... alice@example.com
"""

RETURN = r"""
added_keys:
  description:
    - Keys that were added.
  returned: success
  type: list
  elements: str
  sample: ["ssh-ed25519 AAAA... alice@example.com"]
deleted_keys:
  description:
    - Keys that were deleted, as stored in the account.
  returned: success
  type: list
  elements: str
  sample: ["ssh-ed25519 BBBB... bob@example.com"]
ssh_key:
  description:
    - The account key when exactly one key is given. After deletion, the key before deletion.
    - Empty when more keys are given, or when O(state=absent) and the key did not exist.
  returned: success
  type: dict
  sample:
    id: 7
    alias: laptop
    fingerprint: "SHA256:..."
    key: ssh-ed25519 AAAA... alice@example.com
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.common import PidginHostAPI, drop_none, pidginhost_argument_spec

SSH_KEYS = "/api/account/ssh-keys/"


def key_id(key):
    return " ".join(key.split()[:2])


def main():
    module = AnsibleModule(
        argument_spec=pidginhost_argument_spec(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            ssh_pub_key=dict(type="str", no_log=False),
            ssh_pub_keys=dict(type="list", elements="str", no_log=False),
            alias=dict(type="str"),
            delete_others=dict(type="bool", default=False),
        ),
        mutually_exclusive=[("ssh_pub_key", "ssh_pub_keys")],
        required_one_of=[("ssh_pub_key", "ssh_pub_keys")],
        supports_check_mode=True,
    )
    params = module.params
    present = params["state"] == "present"
    if params["delete_others"] and not present:
        module.fail_json(msg="delete_others requires state=present.")

    alias = params["alias"]
    wanted = params["ssh_pub_keys"] if params["ssh_pub_keys"] is not None else [params["ssh_pub_key"]]
    api = PidginHostAPI(module)
    stored = dict((key_id(k["key"]), k) for k in api.list(SSH_KEYS))
    seen, added, renamed, deleted, result = set(), [], [], [], {}
    for key in wanted:
        if key_id(key) in seen:
            continue
        seen.add(key_id(key))
        current = stored.get(key_id(key))
        if current is None:
            if present:
                added.append(key)
                result = drop_none({"key": key, "alias": alias})
        elif not present:
            deleted.append(current)
            result = current
        elif alias is not None and current.get("alias") != alias:
            renamed.append(current)
            result = dict(current, alias=alias)
        else:
            result = current
    if params["delete_others"]:
        deleted = [k for k in stored.values() if key_id(k["key"]) not in seen]

    if not module.check_mode:
        for key in added:
            result = api.post(SSH_KEYS, drop_none({"key": key, "alias": alias}))
        for key in renamed:
            result = api.patch("%s%s/" % (SSH_KEYS, key["id"]), {"alias": alias})
        for key in deleted:
            api.delete("%s%s/" % (SSH_KEYS, key["id"]))
    module.exit_json(
        changed=bool(added or renamed or deleted),
        added_keys=added,
        deleted_keys=[k["key"] for k in deleted],
        ssh_key=result if len(seen) == 1 else {},
    )


if __name__ == "__main__":
    main()
