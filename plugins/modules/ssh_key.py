# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Popescu Andrei Cristian <andrei.popescu.c@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_key

short_description: Manipulate SSH Keys

version_added: 0.2.0

description:
  - Add all keys from "keys_list".
  - Delete all keys from "keys_list".
  - Add specified SSH keys from "keys_list" and delete any other SSH which are not in "keys_list".
  - View add SSH Key API documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_create).
  - View delete SSH Key documentation at U(https://www.pidginhost.com/api/schema/swagger-ui/#/account/account_ssh_keys_destroy).
author:
  - Popescu Andrei Cristian (@shbpty)

options:
 delete_others:
   description:
     - Keep only the keys specified in "keys_list" and delete others.
   type: bool
   required: false
   choices:
    - true
    - false
 keys_list:
   description:
     - A list of keys, must contain at least one key.
   type: list
   required: true
"""

EXAMPLES = r"""
 - name: Add SSH keys
   pidginhost.cloud.ssh_key:
     state: present
     delete_others: false
     token: "{{ pidgin_host_token }}"
     ssh_pub_key: "{{ item }}"
   with_items: "{{ keys_list }}"
   when: not delete_others

 - name: Delete SSH keys
   pidginhost.cloud.ssh_key:
     state: absent
     delete_others: false
     token: "{{ pidgin_host_token }}"
     ssh_pub_key: "{{ item }}"
   with_items: "{{ keys_list }}"
   when: not delete_others

 - name: Add specified SSH keys and delete any other SSH keys found based on the delete_others flag
   pidginhost.cloud.ssh_key:
     state: present
     delete_others: true
     token: "{{ pidgin_host_token }}"
     ssh_pub_key: "{{ keys_list }}"
   when: delete_others == true and state == 'present'
"""

RETURN = """
ssh_key:
  changed: true
  results:
    - added_keys: []
      ansible_loop_var: "item"
      changed: true
      deleted_keys: []
      deleted_msg: []
      failed: false
      invocation:
        module_args:
          delete_others: false
          ssh_pub_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAgQUhzdiTsW0CwvwOfde/2EOZ40JU5paEHP7ejAO7PB ansible"
          state: "present"
          timeout: 300
          token: "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"
      item: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAgQUhzdiTsW0CwvwOfde/2EOZ40JU5paEHP7ejAO7PB ansible"
      msg: "SSH Pub Key successfully added to cloud"
      ssh_key: []
  skipped: false
  
error:
  description: PidginHost API error.
  returned: failure
  type: dict
  sample:
    Message: PidginHost API error, request to {url} failed.
    Response: response.text
    Status Code: response.status_code
msg:
  description: Action information.
  returned: always
  type: str
  sample:
    - SSH key SSH_KEY fingerprint : (FINGERPRINT) is deleted.
    - Keys will be added to Cloud.
    - SSH Pub Key SSH_KEY already exists on cloud
    - Keys have been added to Cloud.
    - SSH Pub Key will be added to cloud
    - SSH Pub Key successfully added to cloud
    - You need to chose (state: present) if you have (delete_others: true)
    - SSH key SSH_KEY does not exist
    - SSH key SSH_KEY fingerprint : (FINGERPRINT) would be deleted
deleted_msg:
  description: Keys deleted information.
  returned: always
  type: str
  sample:
    - Keys will be deleted from Cloud.
    - Keys have been deleted from Cloud.
deleted_keys:
  description: Deleted Keys.
  returned: always
  type: str
  sample:
    - Lis of Deleted Keys.
added_keys:
  description: Added Keys.
  returned: always
  type: str
  sample:
    - Lis of Added Keys.
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
                        msg=f"SSH Pub Key will be added to cloud",
                        added_keys=[],
                        ssh_key=[],
                    )
                else:
                    self.add_ssh_key(body)
                    self.module.exit_json(
                        changed=True,
                        deleted_msg=[],
                        deleted_keys=[],
                        msg=f"SSH Pub Key successfully added to cloud",
                        added_keys=[],
                        ssh_key=[],

                    )

    def absent(self):
        if self.delete_others:
            self.module.exit_json(
                changed=False,
                deleted_msg=[],
                deleted_keys=[],
                msg=f"You need to chose (state: present) if you have (delete_others: true)",
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
                        msg=f"SSH key {self.ssh_pub_key} fingerprint : ({ssh_pub_key_exist['fingerprint']}) "
                            f"would be deleted",
                        added_keys=[],
                        ssh_key=ssh_pub_key_exist,
                    )
                else:
                    self.delete_ssh_key(ssh_pub_key_exist['id'])
                    self.module.exit_json(
                        changed=True,
                        deleted_msg=[],
                        deleted_keys=[],
                        msg=f"SSH key {self.ssh_pub_key} fingerprint : ({ssh_pub_key_exist['fingerprint']}) "
                            f"is deleted",
                        added_keys=[],
                        ssh_key=ssh_pub_key_exist)


def main():
    argument_spec = PidginHostOptions.argument_spec()
    argument_spec.update(ssh_pub_key=dict(type='str', required=True),
                         delete_others=dict(
                             type=bool,
                             choices=[True, False],
                             default=False,
                             required=False
                         )
                         )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    HandleSSHKeys(module)


if __name__ == '__main__':
    main()
