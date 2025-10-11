# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_key

short_description: Manage SSH keys.

version_added: 0.2.0

description:
  - Add or remove SSH keys for the authenticated account.
  - View the add SSH key API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_create).
  - View the delete SSH key API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_destroy).

author:
  - Popescu Andrei Cristian (@shbpty)

extends_documentation_fragment:
  - pidginhost.cloud.pidginhost

options:
  ssh_pub_key:
    description:
      - SSH public key string or a JSON-encoded list of keys when C(delete_others=true).
    type: str
    required: true
  delete_others:
    description:
      - When true, keep only the provided keys and delete all others.
    type: bool
    required: false
    default: false
"""

EXAMPLES = r"""
- name: Add a single SSH key
  pidginhost.cloud.ssh_key:
    state: present
    ssh_pub_key: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"

- name: Replace all SSH keys with a provided list
  pidginhost.cloud.ssh_key:
    state: present
    delete_others: true
    ssh_pub_key: "{{ ['ssh-ed25519 AAA...', 'ssh-ed25519 BBB...'] | to_json }}"

- name: Remove a specific SSH key
  pidginhost.cloud.ssh_key:
    state: absent
    ssh_pub_key: "ssh-ed25519 AAA..."
"""


from ansible.module_utils.basic import AnsibleModule
from ..module_utils.common import PidginHostCommonModule, PidginHostOptions
import ast


class HandleSSHKeys(PidginHostCommonModule):
    def __init__(self, module):
        super().__init__(module)
        self.token = module.params.get("token")
        self.ssh_pub_key = module.params.get("ssh_pub_key")
        self.delete_others = module.params.get("delete_others")
        if self.delete_others:
            self.ssh_pub_key = ast.literal_eval(self.ssh_pub_key)
        self.delete_others = module.params.get("delete_others")

        self.arguments_max_length(ssh_pub_key=self.ssh_pub_key)

        if self.state == "present":
            self.present()
        if self.state == "absent":
            self.absent()

    def present(self):
        if self.delete_others:
            body = {
                "key": "",
                "token": self.token
            }
            added_keys = list()
            check_keys_data = self.get_ssh_keys()
            cloud_ssh_keys = check_keys_data.get("results")

            diff_ssh_keys = [key["key"] for key in cloud_ssh_keys if
                             key["key"] not in self.ssh_pub_key]

            if self.module.check_mode:
                for k in self.ssh_pub_key:
                    if not self.check_existing_ssh_pub_keys(k):
                        added_keys.append(k)

                self.module.exit_json(
                    changed=True,
                    deleted_msg="Keys will be deleted from Cloud.",
                    deleted_keys=diff_ssh_keys,
                    msg="Keys will be added to Cloud.",
                    added_keys=added_keys,
                    ssh_key=[],
                )
            else:
                for key in self.ssh_pub_key:
                    if not self.check_existing_ssh_pub_keys(key):
                        added_keys.append(key)
                        body["key"] = key
                        self.add_ssh_key(body)
                if diff_ssh_keys:
                    for key in diff_ssh_keys:
                        ssh_pub_key_exist = self.check_existing_ssh_pub_keys(key)
                        if ssh_pub_key_exist:
                            self.delete_ssh_key(ssh_pub_key_exist["id"])

                self.module.exit_json(
                    changed=True,
                    deleted_msg="Keys have been deleted from Cloud.",
                    deleted_keys=diff_ssh_keys,
                    msg="Keys have been added to Cloud.",
                    added_keys=added_keys,
                    ssh_key=[],
                )

        else:
            body = {
                "key": self.ssh_pub_key,
                "token": self.token
            }
            if self.check_existing_ssh_pub_keys(self.ssh_pub_key):
                self.module.fail_json(
                    changed=False,
                    deleted_msg=[],
                    deleted_keys=[],
                    msg=f"SSH Pub Key {self.ssh_pub_key} already exists on cloud",
                    added_keys=[],
                    ssh_key=[],
                )
            else:
                if self.module.check_mode:
                    self.module.exit_json(
                        changed=True,
                        deleted_msg=[],
                        deleted_keys=[],
                        msg="SSH Pub Key will be added to cloud",
                        added_keys=[],
                        ssh_key=[],
                    )
                else:
                    self.add_ssh_key(body)
                    self.module.exit_json(
                        changed=True,
                        deleted_msg=[],
                        deleted_keys=[],
                        msg="SSH Pub Key successfully added to cloud",
                        added_keys=[],
                        ssh_key=[],

                    )

    def absent(self):
        if self.delete_others:
            self.module.exit_json(
                changed=False,
                deleted_msg=[],
                deleted_keys=[],
                msg="You need to choose state=present when delete_others=true",
                added_keys=[],
                ssh_key=[],
            )
        else:
            ssh_pub_key_exist = self.check_existing_ssh_pub_keys(self.ssh_pub_key)
            if not ssh_pub_key_exist:
                self.module.exit_json(
                    changed=False,
                    deleted_msg=[],
                    deleted_keys=[],
                    msg=f"SSH key {self.ssh_pub_key} does not exist",
                    added_keys=[],
                    ssh_key=[],
                )
            elif ssh_pub_key_exist:
                if self.module.check_mode:
                    self.module.exit_json(
                        changed=True,
                        deleted_msg=[],
                        deleted_keys=[],
                        msg=(
                            f"SSH key {self.ssh_pub_key} fingerprint : ({ssh_pub_key_exist['fingerprint']}) "
                            "would be deleted"
                        ),
                        added_keys=[],
                        ssh_key=ssh_pub_key_exist,
                    )
                else:
                    self.delete_ssh_key(ssh_pub_key_exist['id'])
                    self.module.exit_json(
                        changed=True,
                        deleted_msg=[],
                        deleted_keys=[],
                        msg=(
                            f"SSH key {self.ssh_pub_key} fingerprint : ({ssh_pub_key_exist['fingerprint']}) "
                            "is deleted"
                        ),
                        added_keys=[],
                        ssh_key=ssh_pub_key_exist)


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(
        ssh_pub_key=dict(type='str', required=True),
        delete_others=dict(type='bool', default=False, required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    HandleSSHKeys(module)


if __name__ == '__main__':
    main()
